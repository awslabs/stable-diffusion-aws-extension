import datetime
import json
import logging
import os
import tarfile
from dataclasses import dataclass
from typing import Any, List, Optional

import boto3

from common.ddb_service.client import DynamoDbUtilsService
from common.response import bad_request, not_found, forbidden, internal_server_error, created
from common.util import get_s3_presign_urls
from common.util import load_json_from_s3, save_json_to_file
from libs.data_types import TrainJob, TrainJobStatus, Model, CreateModelStatus, CheckPoint, CheckPointStatus
from libs.utils import get_permissions_by_username, get_user_roles

bucket_name = os.environ.get('S3_BUCKET')
train_table = os.environ.get('TRAIN_TABLE')
model_table = os.environ.get('MODEL_TABLE')
checkpoint_table = os.environ.get('CHECKPOINT_TABLE')
user_table = os.environ.get('MULTI_USER_TABLE')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ddb_service = DynamoDbUtilsService(logger=logger)


@dataclass
class Event:
    train_type: str
    model_id: str
    params: dict[str, Any]
    creator: str
    filenames: Optional[List[str]] = None


def handler(raw_event, context):
    request_id = context.aws_request_id
    event = Event(**json.loads(raw_event['body']))
    _type = event.train_type

    try:
        creator_permissions = get_permissions_by_username(ddb_service, user_table, event.creator)
        if 'train' not in creator_permissions \
                or ('all' not in creator_permissions['train'] and 'create' not in creator_permissions['train']):
            return forbidden(message=f'user {event.creator} has not permission to create a train job')

        model_raw = ddb_service.get_item(table=model_table, key_values={
            'id': event.model_id
        })
        # if model is not found, model_raw is {}
        if model_raw == {}:
            return not_found(message=f'model with id {event.model_id} is not found')

        model = Model(**model_raw)
        if model.job_status != CreateModelStatus.Complete:
            return bad_request(
                message=f'model {model.id} is in {model.job_status.value} state, not valid to be used for train')

        base_key = f'{_type}/train/{model.name}/{request_id}'
        input_location = f'{base_key}/input'
        presign_url_map = None
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

                s3 = boto3.client('s3')
                s3.upload_file(tar_file_path, bucket_name, os.path.join(input_location, tar_file_name))
                logger.info(f"Tar file '{tar_file_name}' uploaded to '{bucket_name}' successfully.")
            except Exception as e:
                raise RuntimeError(f"Error uploading JSON file to S3: {e}")
        else:
            presign_url_map = get_s3_presign_urls(bucket_name=bucket_name, base_key=input_location,
                                                  filenames=event.filenames)

        user_roles = get_user_roles(ddb_service, user_table, event.creator)
        checkpoint = CheckPoint(
            id=request_id,
            checkpoint_type=event.train_type,
            s3_location=f's3://{bucket_name}/{base_key}/output',
            checkpoint_status=CheckPointStatus.Initial,
            timestamp=datetime.datetime.now().timestamp(),
            allowed_roles_or_users=user_roles
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
            timestamp=datetime.datetime.now().timestamp(),
            allowed_roles_or_users=[event.creator]
        )
        ddb_service.put_items(table=train_table, entries=train_job.__dict__)

        data = {
            'job': {
                'id': train_job.id,
                'status': train_job.job_status.value,
                'trainType': train_job.train_type,
                'params': train_job.params,
                'input_location': train_input_s3_location,
            },
            's3PresignUrl': presign_url_map
        }

        return created(data=data)
    except Exception as e:
        logger.error(e)
        return internal_server_error(message=str(e))
