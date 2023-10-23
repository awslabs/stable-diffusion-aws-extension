# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import datetime
import json
import logging
import os
import base64
import time
from dataclasses import dataclass
import boto3
import tarfile
from typing import Any, List, Optional
import sagemaker
import tomli
import tomli_w

from common.ddb_service.client import DynamoDbUtilsService
from common.stepfunction_service.client import StepFunctionUtilsService
from common.util import load_json_from_s3, publish_msg, save_json_to_file
from common_tools import split_s3_path, DecimalEncoder
from common.util import get_s3_presign_urls
from common.const import LoraTrainType
from common import const
from _types import TrainJob, TrainJobStatus, Model, CreateModelStatus, CheckPoint, CheckPointStatus


bucket_name = os.environ.get('S3_BUCKET')
train_table = os.environ.get('TRAIN_TABLE')
model_table = os.environ.get('MODEL_TABLE')
checkpoint_table = os.environ.get('CHECKPOINT_TABLE')
instance_type = os.environ.get('INSTANCE_TYPE')
sagemaker_role_arn = os.environ.get('TRAIN_JOB_ROLE')
image_uri = os.environ.get('TRAIN_ECR_URL')  # e.g. "648149843064.dkr.ecr.us-east-1.amazonaws.com/dreambooth-training-repo"
training_stepfunction_arn = os.environ.get('TRAINING_SAGEMAKER_ARN')
user_topic_arn = os.environ.get('USER_EMAIL_TOPIC_ARN')
region_name = os.environ['AWS_REGION']

logger = logging.getLogger('boto3')
ddb_service = DynamoDbUtilsService(logger=logger)
s3 = boto3.client('s3', region_name=region_name)


@dataclass
class Event:
    train_type: str
    params: dict[str, Any]
    model_id: Optional[str] = None
    filenames: Optional[List[str]] = None
    # Valid value: dreambooth, kohya. Default value is dreambooth
    lora_train_type: Optional[str] = LoraTrainType.DREAM_BOOTH.value


def _update_toml_file_in_s3(bucket_name: str, file_key: str, new_file_key: str, updated_params):
    """Update and save a TOML file in an S3 bucket

    Args:
        bucket_name (str): S3 bucket name to save the TOML file
        file_key (str): TOML template file key
        new_file_key (str): TOML file with merged parameters
        updated_params (_type_): parameters to be merged
    """
    try:
        response = s3.get_object(Bucket=bucket_name, Key=file_key)
        toml_content = response['Body'].read().decode('utf-8')
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


# POST /train
def create_train_job_api(raw_event, context):
    request_id = context.aws_request_id
    event = Event(**raw_event)
    _type = event.train_type
    _lora_train_type = event.lora_train_type
    presign_url_map = None

    try:
        if _lora_train_type.lower() == LoraTrainType.KOHYA.value:
            # Kohya training
            base_key = f'{_lora_train_type.lower()}/train/{request_id}'
            input_location = f'{base_key}/input'
            toml_dest_path = f'{input_location}/{const.KOHYA_TOML_FILE_NAME}'
            toml_template_path = 'template/' + const.KOHYA_TOML_FILE_NAME
            if event.model_id is None:
                event.model_id = const.KOHYA_MODEL_ID

            if 'training_params' not in event.params \
                or 's3_model_path' not in event.params['training_params'] \
                    or 's3_data_path' not in event.params['training_params']:
                raise ValueError('Missing train parameters, s3_model_path and s3_data_path should be in training_params')

            # Merge user parameter, if no config_params is defined, use the default value in S3 bucket
            if 'config_params' in event.params:
                updated_parameters = event.params['config_params']
                _update_toml_file_in_s3(bucket_name, toml_template_path, toml_dest_path, updated_parameters)
            else:
                # Copy template file and make no changes as no config parameters are defined
                s3.copy_object(
                    CopySource={'Bucket': bucket_name, 'Key': toml_template_path},
                    Bucket=bucket_name,
                    Key=toml_dest_path
                )
            
            event.params['training_params']['s3_toml_path'] = f's3://{bucket_name}/{toml_dest_path}'
        elif _lora_train_type.lower() == LoraTrainType.DREAM_BOOTH.value:
            # DreamBooth training
            if event.model_id is None:
                raise ValueError('No model_id is specified.')

            model_raw = ddb_service.get_item(table=model_table, key_values={
                'id': event.model_id
            })
            if model_raw is None:
                return {
                    'statusCode': 500,
                    'error': f'model with id {event.model_id} is not found'
                }

            model = Model(**model_raw)
            if model.job_status != CreateModelStatus.Complete:
                return {
                    'statusCode': 500,
                    'error': f'model {model.id} is in {model.job_status.value} state, not valid to be used for train'
                }

            base_key = f'{_type}/train/{model.name}/{request_id}'
            input_location = f'{base_key}/input'
            if event.filenames is None:
                # Invoked from api, no config file is defined in the parameters
                json_file_name = 'db_config_cloud.json'
                tar_file_name = 'db_config.tar'
                tar_file_content = f'/tmp/models/sagemaker_dreambooth/{model.name}'
                tar_file_path = f'/tmp/{tar_file_name}'

                db_config_json = load_json_from_s3(bucket_name, 'template/' + json_file_name)
                # Merge user parameter, if no config_params is defined, use the default value in S3 bucket
                if "config_params" in event.params:
                    db_config_json.update(event.params["config_params"])
                
                # Add model parameters into train params
                event.params["training_params"]["model_name"] = model.name
                event.params["training_params"]["model_type"] = model.model_type
                event.params["training_params"]["s3_model_path"] = model.output_s3_location

                # Upload the merged JSON string to the S3 bucket as a tar file
                try:
                    if not os.path.exists(tar_file_content):
                        os.makedirs(tar_file_content)
                    saved_path = save_json_to_file(db_config_json, tar_file_content, json_file_name)
                    print(f'file saved to {saved_path}')
                    with tarfile.open('/tmp/' + tar_file_name, 'w') as tar:
                        # Add the contents of 'models' directory to the tar file without including the /tmp itself
                        tar.add(tar_file_content, arcname=f'models/sagemaker_dreambooth/{model.name}')
                    s3.upload_file(tar_file_path, bucket_name, os.path.join(input_location, tar_file_name))
                    logger.info(f"Tar file '{tar_file_name}' uploaded to '{bucket_name}' successfully.")
                except Exception as e:
                    raise RuntimeError(f"Error uploading JSON file to S3: {e}")
            else:    
                presign_url_map = get_s3_presign_urls(bucket_name=bucket_name, base_key=input_location, filenames=event.filenames)
        else:
            raise ValueError(f'Invalid lora train type: {_lora_train_type}, the valid value is {LoraTrainType.KOHYA.value} and {LoraTrainType.DREAM_BOOTH.value}.')

        event.params['training_type'] = _lora_train_type.lower()
        checkpoint = CheckPoint(
            id=request_id,
            checkpoint_type=event.train_type,
            s3_location=f's3://{bucket_name}/{base_key}/output',
            checkpoint_status=CheckPointStatus.Initial,
            timestamp=datetime.datetime.now().timestamp(),
            allowed_roles_or_users=['*']  # fixme: not in scope yet, need fix later for train process
        )
        ddb_service.put_items(table=checkpoint_table, entries=checkpoint.__dict__)
        train_input_s3_location = f's3://{bucket_name}/{input_location}'
        
        train_job = TrainJob(
            id=request_id,
            model_id=event.model_id,
            job_status=TrainJobStatus.Initial,
            params=event.params,
            train_type=event.train_type,
            input_s3_location=train_input_s3_location,
            checkpoint_id=checkpoint.id,
            timestamp=datetime.datetime.now().timestamp()
        )
        ddb_service.put_items(table=train_table, entries=train_job.__dict__)

        return {
            'statusCode': 200,
            'job': {
                'id': train_job.id,
                'status': train_job.job_status.value,
                'trainType': train_job.train_type,
                'params': train_job.params,
                'input_location': train_input_s3_location,
            },
            's3PresignUrl': presign_url_map
        }
    except Exception as e:
        logger.error(e)

        return {
            'statusCode': 200,
            'error': str(e)
        }


# GET /trains
def list_all_train_jobs_api(event, context):
    _filter = {}
    if 'queryStringParameters' not in event:
        return {
            'statusCode': '500',
            'error': 'query parameter status and types are needed'
        }

    parameters = event['queryStringParameters']
    if 'types' in parameters and len(parameters['types']) > 0:
        _filter['train_type'] = parameters['types']

    if 'status' in parameters and len(parameters['status']) > 0:
        _filter['job_status'] = parameters['status']

    resp = ddb_service.scan(table=train_table, filters=_filter)
    if resp is None or len(resp) == 0:
        return {
            'statusCode': 200,
            'trainJobs': []
        }

    train_jobs = []
    for tr in resp:
        train_job = TrainJob(**(ddb_service.deserialize(tr)))
        model_name = 'not_applied'
        if 'training_params' in train_job.params and 'model_name' in train_job.params['training_params']:
            model_name = train_job.params['training_params']['model_name']

        train_jobs.append({
            'id': train_job.id,
            'modelName': model_name,
            'status': train_job.job_status.value,
            'trainType': train_job.train_type,
            'created': train_job.timestamp,
            'sagemakerTrainName': train_job.sagemaker_train_name,
        })

    return {
        'statusCode': 200,
        'trainJobs': train_jobs
    }


# PUT /train used to kickoff a train job step function
def update_train_job_api(event, context):
    if 'status' in event and 'train_job_id' in event and event['status'] == TrainJobStatus.Training.value:
        return _start_train_job(event['train_job_id'])

    return {
        'statusCode': 200,
        'msg': f'not implemented for train job status {event["status"]}'
    }


# JSON encode hyperparameters
def _json_encode_hyperparameters(hyperparameters):
    new_params = {}
    for k, v in hyperparameters.items():
        json_v = json.dumps(v, cls=DecimalEncoder)
        v_bytes = json_v.encode('ascii')
        base64_bytes = base64.b64encode(v_bytes)
        base64_v = base64_bytes.decode('ascii')
        new_params[k] = base64_v
    return new_params


def _trigger_sagemaker_training_job(train_job: TrainJob, ckpt_output_path: str, train_job_name: str):
    """Trigger SageMaker training job

    Args:
        train_job (TrainJob): training job metadata
        ckpt_output_path (str): S3 path to store the trained model file
        train_job_name (str): training job name
    """
    hyperparameters = _json_encode_hyperparameters({
        "sagemaker_program": "extensions/sd-webui-sagemaker/sagemaker_entrypoint_json.py",
        "params": train_job.params,
        "s3-input-path": train_job.input_s3_location,
        "s3-output-path": ckpt_output_path,
        "training-type": train_job.params['training_type'] # Available value: "dreambooth", "kohya"
    })

    final_instance_type = instance_type
    if 'training_params' in train_job.params \
            and 'training_instance_type' in train_job.params['training_params'] and \
            train_job.params['training_params']['training_instance_type']:
        final_instance_type = train_job.params['training_params']['training_instance_type']

    est = sagemaker.estimator.Estimator(
        image_uri,
        sagemaker_role_arn,
        instance_count=1,
        instance_type=final_instance_type,
        volume_size=125,
        base_job_name=f'{train_job_name}',
        hyperparameters=hyperparameters,
        job_id=train_job.id,
    )
    est.fit(wait=False)

    while not est._current_job_name:
        time.sleep(1)

    train_job.sagemaker_train_name = est._current_job_name
    # trigger stepfunction
    stepfunctions_client = StepFunctionUtilsService(logger=logger)
    sfn_input = {
        'train_job_id': train_job.id,
        'train_job_name': train_job.sagemaker_train_name
    }
    sfn_arn = stepfunctions_client.invoke_step_function(training_stepfunction_arn, sfn_input)
    # todo: use batch update, this is ugly!!!
    search_key = {'id': train_job.id}
    ddb_service.update_item(
        table=train_table,
        key=search_key,
        field_name='sagemaker_train_name',
        value=est._current_job_name
    )
    train_job.job_status = TrainJobStatus.Training
    ddb_service.update_item(
        table=train_table,
        key=search_key,
        field_name='job_status',
        value=TrainJobStatus.Training.value
    )
    train_job.sagemaker_sfn_arn = sfn_arn
    ddb_service.update_item(
        table=train_table,
        key=search_key,
        field_name='sagemaker_sfn_arn',
        value=sfn_arn
    )


def _start_train_job(train_job_id: str):
    raw_train_job = ddb_service.get_item(table=train_table, key_values={
        'id': train_job_id
    })
    if raw_train_job is None or len(raw_train_job) == 0:
        return {
            'statusCode': 500,
            'error': f'no such train job with id({train_job_id})'
        }

    train_job = TrainJob(**raw_train_job)

    if train_job.model_id == const.KOHYA_MODEL_ID:
        train_job_name = train_job.model_id
    else:
        model_raw = ddb_service.get_item(table=model_table, key_values={
            'id': train_job.model_id
        })
        if model_raw is None:
            return {
                'statusCode': 500,
                'error': f'model with id {train_job.model_id} is not found'
            }

        model = Model(**model_raw)
        train_job_name = model.name

    raw_checkpoint = ddb_service.get_item(table=checkpoint_table, key_values={
        'id': train_job.checkpoint_id
    })
    if raw_checkpoint is None:
        return {
            'statusCode': 500,
            'error': f'checkpoint with id {train_job.checkpoint_id} is not found'
        }

    checkpoint = CheckPoint(**raw_checkpoint)

    try:
        _trigger_sagemaker_training_job(train_job, checkpoint.s3_location, train_job_name)

        return {
            'statusCode': 200,
            'job': {
                'id': train_job.id,
                'status': train_job.job_status.value,
                'created': train_job.timestamp,
                'trainType': train_job.train_type,
                'params': train_job.params,
                'input_location': train_job.input_s3_location
            },
        }
    except Exception as e:
        print(e)
        return {
            'statusCode': 500,
            'error': str(e)
        }


# sfn
def check_train_job_status(event, context):
    boto3_sagemaker = boto3.client('sagemaker')
    train_job_name = event['train_job_name']
    train_job_id = event['train_job_id']

    resp = boto3_sagemaker.describe_training_job(
        TrainingJobName=train_job_name
    )

    training_job_status = resp['TrainingJobStatus']
    event['status'] = training_job_status

    raw_train_job = ddb_service.get_item(table=train_table, key_values={
        'id': train_job_id,
    })

    if raw_train_job is None or len(raw_train_job) == 0:
        event['status'] = 'Failed'
        return {
            'statusCode': 500,
            'msg': f'no such training job find in ddb id[{train_job_id}]'
        }

    training_job = TrainJob(**raw_train_job)
    if training_job_status == 'InProgress' or training_job_status == 'Stopping':
        return event

    if training_job_status == 'Failed' or training_job_status == 'Stopped':
        training_job.job_status = TrainJobStatus.Fail
        if 'FailureReason' in resp:
            err_msg = resp['FailureReason']
            training_job.params['resp'] = {
                'status': 'Failed',
                'error_msg': err_msg,
                'raw_resp': resp
            }

    if training_job_status == 'Completed':
        training_job.job_status = TrainJobStatus.Complete
        # todo: update checkpoints
        raw_checkpoint = ddb_service.get_item(table=checkpoint_table, key_values={
            'id': training_job.checkpoint_id
        })
        if raw_checkpoint is None or len(raw_checkpoint) == 0:
            # todo: or create new one
            return 'failed because no checkpoint, not normal'

        checkpoint = CheckPoint(**raw_checkpoint)
        checkpoint.checkpoint_status = CheckPointStatus.Active
        s3 = boto3.client('s3')
        bucket, key = split_s3_path(checkpoint.s3_location)
        s3_resp = s3.list_objects(
            Bucket=bucket,
            Prefix=key,
        )
        checkpoint.checkpoint_names = []
        if 'Contents' in s3_resp and len(s3_resp['Contents']) > 0:
            for obj in s3_resp['Contents']:
                checkpoint_name = obj['Key'].replace(f'{key}/', "")
                checkpoint.checkpoint_names.append(checkpoint_name)
        else:
            training_job.job_status = TrainJobStatus.Fail
            checkpoint.checkpoint_status = CheckPointStatus.Initial

        ddb_service.update_item(
            table=checkpoint_table,
            key={
                'id': checkpoint.id
            },
            field_name='checkpoint_status',
            value=checkpoint.checkpoint_status.value
        )
        ddb_service.update_item(
            table=checkpoint_table,
            key={
                'id': checkpoint.id
            },
            field_name='checkpoint_names',
            value=checkpoint.checkpoint_names
        )

        training_job.params['resp'] = {
            'raw_resp': resp
        }

    # fixme: this is ugly
    ddb_service.update_item(
        table=train_table,
        key={'id': training_job.id},
        field_name='job_status',
        value=training_job.job_status.value
    )

    ddb_service.update_item(
        table=train_table,
        key={'id': training_job.id},
        field_name='params',
        value=training_job.params
    )

    return event


# sfn
def process_train_job_result(event, context):
    train_job_id = event['train_job_id']

    raw_train_job = ddb_service.get_item(table=train_table, key_values={
        'id': train_job_id,
    })

    if raw_train_job is None or len(raw_train_job) == 0:
        return {
            'statusCode': 500,
            'msg': f'no such training job find in ddb id[{train_job_id}]'
        }

    train_job = TrainJob(**raw_train_job)

    publish_msg(
        topic_arn=user_topic_arn,
        subject=f'Create Model Job {train_job.sagemaker_train_name} {train_job.job_status}',
        msg=f'to be done with resp: \n {train_job.job_status}'
    )  # todo: find out msg

    return 'job completed'
