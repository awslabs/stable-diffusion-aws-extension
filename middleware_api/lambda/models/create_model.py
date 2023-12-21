import dataclasses
import dataclasses
import datetime
import json
import logging
import os
from typing import Any, Optional

from botocore.exceptions import ClientError

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok, bad_request, internal_server_error
from common.stepfunction_service.client import StepFunctionUtilsService
from lib._types import Model, CreateModelStatus, CheckPoint, CheckPointStatus, MultipartFileReq
from lib.common_tools import get_base_model_s3_key, get_base_checkpoint_s3_key, \
    batch_get_s3_multipart_signed_urls
from multi_users.utils import get_permissions_by_username, get_user_roles

bucket_name = os.environ.get('S3_BUCKET')
model_table = os.environ.get('DYNAMODB_TABLE')
checkpoint_table = os.environ.get('CHECKPOINT_TABLE')
endpoint_name = os.environ.get('SAGEMAKER_ENDPOINT_NAME')
user_table = os.environ.get('MULTI_USER_TABLE')

success_topic_arn = os.environ.get('SUCCESS_TOPIC_ARN')
error_topic_arn = os.environ.get('ERROR_TOPIC_ARN')
user_topic_arn = os.environ.get('USER_TOPIC_ARN')

logger = logging.getLogger('boto3')
logger.setLevel(logging.INFO)
ddb_service = DynamoDbUtilsService(logger=logger)
stepfunctions_client = StepFunctionUtilsService(logger=logger)


@dataclasses.dataclass
class Event:
    model_type: str
    name: str
    params: dict[str, Any]
    filenames: [MultipartFileReq]
    creator: str
    checkpoint_id: Optional[str] = ""


# POST /model
def handler(raw_event, context):
    logger.info(json.dumps(raw_event))
    request_id = context.aws_request_id
    event = Event(**json.loads(raw_event['body']))
    _type = event.model_type

    try:
        # check if roles has already linked to an endpoint?
        creator_permissions = get_permissions_by_username(ddb_service, user_table, event.creator)
        if 'train' not in creator_permissions \
                or ('all' not in creator_permissions['train'] and 'create' not in creator_permissions['train']):
            return bad_request(message=f'user {event.creator} has not permission to create a train job')

        user_roles = get_user_roles(ddb_service, user_table, event.creator)

        # todo: check if duplicated name and new_model_name only for Completed and Model
        if not event.checkpoint_id and len(event.filenames) == 0:
            return bad_request(message='either checkpoint_id or filenames need to be provided')

        base_key = get_base_model_s3_key(_type, event.name, request_id)
        timestamp = datetime.datetime.now().timestamp()
        multiparts_resp = {}
        if not event.checkpoint_id:
            checkpoint_base_key = get_base_checkpoint_s3_key(_type, event.name, request_id)
            presign_url_map = batch_get_s3_multipart_signed_urls(
                bucket_name=bucket_name,
                base_key=checkpoint_base_key,
                filenames=event.filenames
            )
            filenames_only = []
            for f in event.filenames:
                file = MultipartFileReq(**f)
                filenames_only.append(file.filename)

            checkpoint_params = {'created': str(datetime.datetime.now()), 'multipart_upload': {
            }}

            for key, val in presign_url_map.items():
                checkpoint_params['multipart_upload'][key] = {
                    'upload_id': val['upload_id'],
                    'bucket': val['bucket'],
                    'key': val['key'],
                }
                multiparts_resp[key] = val['s3_signed_urls']

            checkpoint = CheckPoint(
                id=request_id,
                checkpoint_type=event.model_type,
                s3_location=f's3://{bucket_name}/{get_base_checkpoint_s3_key(_type, event.name, request_id)}',
                checkpoint_names=filenames_only,
                checkpoint_status=CheckPointStatus.Initial,
                params=checkpoint_params,
                timestamp=timestamp,
                allowed_roles_or_users=user_roles,
            )
            ddb_service.put_items(table=checkpoint_table, entries=checkpoint.__dict__)
            checkpoint_id = checkpoint.id
        else:
            raw_checkpoint = ddb_service.get_item(table=checkpoint_table, key_values={
                'id': event.checkpoint_id,
            })
            if raw_checkpoint is None:
                return bad_request(message=f'create model ckpt with id {event.checkpoint_id} is not found')

            checkpoint = CheckPoint(**raw_checkpoint)
            if checkpoint.checkpoint_status != CheckPointStatus.Active:
                return bad_request(message=f'checkpoint with id ({checkpoint.id}) is not Active to use')
            checkpoint_id = checkpoint.id
            if checkpoint.allowed_roles_or_users:
                allowed_to_use = False
                for role in checkpoint.allowed_roles_or_users:
                    if role in user_roles or '*' == role:
                        allowed_to_use = True
                        break

                if not allowed_to_use:
                    return bad_request(
                        message=f'checkpoint with id ({checkpoint.id}) is not allowed to use by user {event.creator}')

        model_job = Model(
            id=request_id,
            name=event.name,
            output_s3_location=f's3://{bucket_name}/{base_key}/output',
            checkpoint_id=checkpoint_id,
            model_type=_type,
            job_status=CreateModelStatus.Initial,
            params=event.params,
            timestamp=timestamp,
            allowed_roles_or_users=[event.creator]
        )
        ddb_service.put_items(table=model_table, entries=model_job.__dict__)

    except ClientError as e:
        logger.error(e)
        return internal_server_error(message=str(e))

    data = {
        'job': {
            'id': model_job.id,
            'status': model_job.job_status.value,
            's3_base': checkpoint.s3_location,
            'model_type': model_job.model_type,
            'params': model_job.params  # not safe if not json serializable type
        },
        's3PresignUrl': multiparts_resp
    }

    return ok(data=data)
