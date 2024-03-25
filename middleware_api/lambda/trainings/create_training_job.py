import base64
import datetime
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Optional

import boto3
import sagemaker
import time
import tomli
import tomli_w

from common import const
from common.const import LoraTrainType, PERMISSION_TRAIN_ALL
from common.ddb_service.client import DynamoDbUtilsService
from common.excepts import BadRequestException
from common.response import (
    not_found, created,
)
from common.util import query_data
from libs.common_tools import DecimalEncoder
from libs.data_types import (
    CheckPoint,
    CheckPointStatus,
    TrainJob,
    TrainJobStatus,
)
from libs.utils import get_user_roles, permissions_check, response_error, log_json

bucket_name = os.environ.get("S3_BUCKET")
train_table = os.environ.get("TRAIN_TABLE")
checkpoint_table = os.environ.get("CHECKPOINT_TABLE")
user_table = os.environ.get("MULTI_USER_TABLE")
dataset_info_table = os.environ.get("DATASET_INFO_TABLE")
region = os.environ.get("AWS_REGION")
instance_type = os.environ.get("INSTANCE_TYPE")
sagemaker_role_arn = os.environ.get("TRAIN_JOB_ROLE")
image_uri = os.environ.get("TRAIN_ECR_URL")

ddb_client = boto3.client('dynamodb')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL") or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)
s3 = boto3.client("s3", region_name=region)


@dataclass
class Event:
    params: dict[str, Any]
    lora_train_type: Optional[str] = LoraTrainType.KOHYA.value


def _update_toml_file_in_s3(
        bucket_name: str, file_key: str, new_file_key: str, updated_params
):
    """Update and save a TOML file in an S3 bucket

    Args:
        bucket_name (str): S3 bucket name to save the TOML file
        file_key (str): TOML template file key
        new_file_key (str): TOML file with merged parameters
        updated_params (_type_): parameters to be merged
    """
    try:
        response = s3.get_object(Bucket=bucket_name, Key=file_key)
        toml_content = response["Body"].read().decode("utf-8")
        toml_data = tomli.loads(toml_content)

        # Update parameters in the TOML data
        for section, params in updated_params.items():
            if section in toml_data:
                for key, value in params.items():
                    toml_data[section][key] = value
            else:
                toml_data[section] = params

        updated_toml_content = tomli_w.dumps(toml_data)
        s3.put_object(Bucket=bucket_name, Key=new_file_key, Body=updated_toml_content)
        logger.info(f"Updated '{file_key}' in '{bucket_name}' successfully.")

    except Exception as e:
        logger.error(f"An error occurred when updating Kohya toml: {e}")


def _json_encode_hyperparameters(hyperparameters):
    """Encode hyperparameters

    Args:
        hyperparameters : hyperparameters to be encoded

    Returns:
        Encoded hyperparameters
    """
    new_params = {}
    for k, v in hyperparameters.items():
        if region.startswith("cn"):
            new_params[k] = json.dumps(v, cls=DecimalEncoder)
        else:
            json_v = json.dumps(v, cls=DecimalEncoder)
            v_bytes = json_v.encode("ascii")
            base64_bytes = base64.b64encode(v_bytes)
            base64_v = base64_bytes.decode("ascii")
            new_params[k] = base64_v

    return new_params


def _trigger_sagemaker_training_job(
        train_job: TrainJob, ckpt_output_path: str, train_job_name: str
):
    """Trigger a SageMaker training job

    Args:
        train_job (TrainJob): training job metadata
        ckpt_output_path (str): S3 path to store the trained model file
        train_job_name (str): training job name
    """
    hyperparameters = _json_encode_hyperparameters(
        {
            "sagemaker_program": "extensions/sd-webui-sagemaker/sagemaker_entrypoint_json.py",
            "params": train_job.params,
            "s3-input-path": train_job.input_s3_location,
            "s3-output-path": ckpt_output_path,
            "training-type": train_job.params[
                "training_type"
            ],  # Available value: "kohya"
        }
    )

    final_instance_type = instance_type
    if (
            "training_params" in train_job.params
            and "training_instance_type" in train_job.params["training_params"]
            and train_job.params["training_params"]["training_instance_type"]
    ):
        final_instance_type = train_job.params["training_params"][
            "training_instance_type"
        ]

    est = sagemaker.estimator.Estimator(
        image_uri,
        sagemaker_role_arn,
        instance_count=1,
        instance_type=final_instance_type,
        volume_size=125,
        base_job_name=f"{train_job_name}",
        hyperparameters=hyperparameters,
        job_id=train_job.id,
    )
    est.fit(wait=False)

    while not est._current_job_name:
        time.sleep(1)

    train_job.sagemaker_train_name = est._current_job_name

    search_key = {"id": train_job.id}
    ddb_service.update_item(
        table=train_table,
        key=search_key,
        field_name="sagemaker_train_name",
        value=est._current_job_name,
    )
    train_job.job_status = TrainJobStatus.Training
    ddb_service.update_item(
        table=train_table,
        key=search_key,
        field_name="job_status",
        value=TrainJobStatus.Starting.value,
    )


def _start_training_job(train_job_id: str):
    raw_train_job = ddb_service.get_item(
        table=train_table, key_values={"id": train_job_id}
    )
    if raw_train_job is None or len(raw_train_job) == 0:
        return not_found(message=f"no such train job with id({train_job_id})")

    train_job = TrainJob(**raw_train_job)
    train_job_name = train_job.model_id

    raw_checkpoint = ddb_service.get_item(
        table=checkpoint_table, key_values={"id": train_job.checkpoint_id}
    )
    if raw_checkpoint is None:
        return not_found(
            message=f"checkpoint with id {train_job.checkpoint_id} is not found"
        )

    checkpoint = CheckPoint(**raw_checkpoint)

    _trigger_sagemaker_training_job(train_job, checkpoint.s3_location, train_job_name)

    return {
        "id": train_job.id,
        "status": train_job.job_status.Starting.value,
        "created": str(train_job.timestamp),
        "params": train_job.params,
        "input_location": train_job.input_s3_location,
        "output_location": checkpoint.s3_location
    }


def get_model_location(model_name):
    resp = ddb_client.scan(
        TableName=checkpoint_table,
    )

    for item in resp['Items']:
        if 'checkpoint_names' not in item:
            continue
        if 'L' not in item['checkpoint_names']:
            continue
        if len(item['checkpoint_names']['L']) == 0:
            continue
        if item['checkpoint_names']['L'][0]['S'] == model_name:
            return f'{item["s3_location"]["S"]}/{model_name}'

    raise BadRequestException("Model not found")


def get_dataset_location(dataset_name):
    dataset_items = ddb_service.query_items(table=dataset_info_table, key_values={
        'dataset_name': dataset_name,
    })

    if len(dataset_items) == 0:
        raise BadRequestException("Dataset not found")

    return f"s3://{bucket_name}/dataset/{dataset_name}"


def _create_training_job(raw_event, context):
    """Create a training job

    Returns:
        Training job in JSON format
    """
    request_id = context.aws_request_id
    event = Event(**json.loads(raw_event["body"]))
    logger.info(json.dumps(json.loads(raw_event["body"])))
    _lora_train_type = event.lora_train_type

    username = permissions_check(raw_event, [PERMISSION_TRAIN_ALL])

    if _lora_train_type.lower() == LoraTrainType.KOHYA.value:
        # Kohya training
        base_key = f"{_lora_train_type.lower()}/train/{request_id}"
        input_location = f"{base_key}/input"

        model_name = query_data(event.params, ['training_params', 'model'])
        dataset_name = query_data(event.params, ['training_params', 'dataset'])
        fm_type = query_data(event.params, ['training_params', 'fm_type'])
        output_name = query_data(event.params, ['config_params', 'saving_arguments', 'output_name'])

        save_every_n_epochs = query_data(event.params, ['config_params', 'saving_arguments', 'save_every_n_epochs'])
        event.params["config_params"]["saving_arguments"]["save_every_n_epochs"] = int(save_every_n_epochs)

        max_train_epochs = query_data(event.params, ['config_params', 'training_arguments', 'max_train_epochs'])
        event.params["config_params"]["training_arguments"]["max_train_epochs"] = int(max_train_epochs)

        event.params["training_params"]["s3_model_path"] = get_model_location(model_name)
        del event.params['training_params']['model']

        event.params["training_params"]["s3_data_path"] = get_dataset_location(dataset_name)
        del event.params['training_params']['dataset']

        log_json('event', event.__dict__)

        if fm_type.lower() == const.TrainFMType.SD_1_5.value:
            toml_dest_path = f"{input_location}/{const.KOHYA_TOML_FILE_NAME}"
            toml_template_path = "template/" + const.KOHYA_TOML_FILE_NAME
        elif fm_type.lower() == const.TrainFMType.SD_XL.value:
            toml_dest_path = f"{input_location}/{const.KOHYA_XL_TOML_FILE_NAME}"
            toml_template_path = "template/" + const.KOHYA_XL_TOML_FILE_NAME
        else:
            raise BadRequestException(
                f"Invalid fm_type {fm_type}, the valid values are {const.TrainFMType.SD_1_5.value} "
                f"and {const.TrainFMType.SD_XL.value}"
            )

        # Merge user parameter, if no config_params is defined, use the default value in S3 bucket
        if "config_params" in event.params:
            updated_parameters = event.params["config_params"]
            _update_toml_file_in_s3(
                bucket_name, toml_template_path, toml_dest_path, updated_parameters
            )
        else:
            # Copy template file and make no changes as no config parameters are defined
            s3.copy_object(
                CopySource={"Bucket": bucket_name, "Key": toml_template_path},
                Bucket=bucket_name,
                Key=toml_dest_path,
            )

        event.params["training_params"][
            "s3_toml_path"
        ] = f"s3://{bucket_name}/{toml_dest_path}"
    else:
        raise BadRequestException(
            f"Invalid lora train type: {_lora_train_type}, the valid value is {LoraTrainType.KOHYA.value}."
        )

    event.params["training_type"] = _lora_train_type.lower()
    user_roles = get_user_roles(ddb_service, user_table, username)
    ckpt_type = const.CheckPointType.LORA
    if "config_params" in event.params and \
            "additional_network" in event.params["config_params"] and \
            "network_module" in event.params["config_params"]["additional_network"]:
        network_module = event.params["config_params"]["additional_network"]["network_module"]
        if network_module.lower() != const.NetworkModule.LORA:
            ckpt_type = const.CheckPointType.SD

    checkpoint = CheckPoint(
        id=request_id,
        checkpoint_type=ckpt_type,
        checkpoint_names=[output_name],
        s3_location=f"s3://{bucket_name}/{base_key}/output",
        checkpoint_status=CheckPointStatus.Initial,
        timestamp=datetime.datetime.now().timestamp(),
        allowed_roles_or_users=user_roles,
    )
    ddb_service.put_items(table=checkpoint_table, entries=checkpoint.__dict__)
    train_input_s3_location = f"s3://{bucket_name}/{input_location}"

    train_job = TrainJob(
        id=request_id,
        model_id=const.KOHYA_MODEL_ID,
        job_status=TrainJobStatus.Initial,
        params=event.params,
        train_type=const.TRAIN_TYPE,
        input_s3_location=train_input_s3_location,
        checkpoint_id=checkpoint.id,
        timestamp=datetime.datetime.now().timestamp(),
        allowed_roles_or_users=[username],
    )
    ddb_service.put_items(table=train_table, entries=train_job.__dict__)

    return train_job.id


def handler(raw_event, context):
    job_id = None
    try:
        logger.info(json.dumps(raw_event))

        job_id = _create_training_job(raw_event, context)
        job_info = _start_training_job(job_id)

        return created(data=job_info, decimal=True)
    except Exception as e:
        if job_id:
            ddb_service.delete_item(train_table, keys={
                'id': job_id,
            })
        return response_error(e)
