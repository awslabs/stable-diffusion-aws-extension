import datetime
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict

from _types import CheckPoint, CheckPointStatus, MultipartFileReq
from common.ddb_service.client import DynamoDbUtilsService
from common_tools import get_base_checkpoint_s3_key, \
    batch_get_s3_multipart_signed_urls, complete_multipart_upload
from multi_users.utils import get_user_roles, check_user_permissions

checkpoint_table = os.environ.get('CHECKPOINT_TABLE')
bucket_name = os.environ.get('S3_BUCKET')
user_table = os.environ.get('MULTI_USER_TABLE')

logger = logging.getLogger('boto3')
ddb_service = DynamoDbUtilsService(logger=logger)


# GET /checkpoints?username=USER_NAME&types=value&status=value
def list_all_checkpoints_api(event, context):
    _filter = {}
    if 'queryStringParameters' not in event:
        return {
            'statusCode': '500',
            'error': 'query parameter status and types are needed'
        }
    parameters = event['queryStringParameters']
    if 'types' in parameters and len(parameters['types']) > 0:
        _filter['checkpoint_type'] = parameters['types']

    if 'status' in parameters and len(parameters['status']) > 0:
        _filter['checkpoint_status'] = parameters['status']

    username = parameters['username'] if 'username' in parameters and parameters['username'] else 0
    user_roles = ['*']
    if username:
        user_roles = get_user_roles(ddb_service=ddb_service, user_table_name=user_table, username=username)

    raw_ckpts = ddb_service.scan(table=checkpoint_table, filters=_filter)
    if raw_ckpts is None or len(raw_ckpts) == 0:
        return {
            'statusCode': 200,
            'checkpoints': []
        }

    ckpts = []
    for r in raw_ckpts:
        ckpt = CheckPoint(**(ddb_service.deserialize(r)))
        if check_user_permissions(ckpt.allowed_roles_or_users, user_roles, username):
            ckpts.append({
                'id': ckpt.id,
                's3Location': ckpt.s3_location,
                'type': ckpt.checkpoint_type,
                'status': ckpt.checkpoint_status.value,
                'name': ckpt.checkpoint_names,
                'created': ckpt.timestamp,
            })
    return {
        'statusCode': 200,
        'checkpoints': ckpts
    }


@dataclass
class CreateCheckPointEvent:
    checkpoint_type: str
    filenames: [MultipartFileReq]
    params: dict[str, Any]


# POST /checkpoint
def create_checkpoint_api(raw_event, context):
    request_id = context.aws_request_id
    event = CreateCheckPointEvent(**raw_event)
    _type = event.checkpoint_type
    headers = {
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
    }
    try:
        base_key = get_base_checkpoint_s3_key(_type, 'custom', request_id)
        presign_url_map = batch_get_s3_multipart_signed_urls(
            bucket_name=bucket_name,
            base_key=base_key,
            filenames=event.filenames
        )

        checkpoint_params = {}
        if event.params is not None and len(event.params) > 0:
            checkpoint_params = event.params

        checkpoint_params['created'] = str(datetime.datetime.now())
        checkpoint_params['multipart_upload'] = {}
        multiparts_resp = {}
        for key, val in presign_url_map.items():
            checkpoint_params['multipart_upload'][key] = {
                'upload_id': val['upload_id'],
                'bucket': val['bucket'],
                'key': val['key'],
            }
            multiparts_resp[key] = val['s3_signed_urls']

        filenames_only = []
        for f in event.filenames:
            file = MultipartFileReq(**f)
            filenames_only.append(file.filename)

        if len(filenames_only) == 0:
            return {
                'statusCode': 400,
                'headers': headers,
                'errorMsg': 'no checkpoint name (file names) detected'
            }

        user_roles = ['*']
        if 'creator' in event.params and event.params['creator']:
            user_roles = get_user_roles(ddb_service, user_table, event.params['creator'])

        checkpoint = CheckPoint(
            id=request_id,
            checkpoint_type=_type,
            s3_location=f's3://{bucket_name}/{base_key}',
            checkpoint_names=filenames_only,
            checkpoint_status=CheckPointStatus.Initial,
            params=checkpoint_params,
            timestamp=datetime.datetime.now().timestamp(),
            allowed_roles_or_users=user_roles
        )
        ddb_service.put_items(table=checkpoint_table, entries=checkpoint.__dict__)
        return {
            'statusCode': 200,
            'headers': headers,
            'checkpoint': {
                'id': request_id,
                'type': _type,
                's3_location': checkpoint.s3_location,
                'status': checkpoint.checkpoint_status.value,
                'params': checkpoint.params
            },
            's3PresignUrl': multiparts_resp
        }
    except Exception as e:
        logger.error(e)
        return {
            'statusCode': 500,
            'headers': headers,
            'error': str(e)
        }


@dataclass
class UpdateCheckPointEvent:
    checkpoint_id: str
    status: str
    multi_parts_tags: Dict[str, Any]


# PUT /checkpoint
def update_checkpoint_api(raw_event, context):
    event = UpdateCheckPointEvent(**raw_event)
    headers = {
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
    }
    try:
        raw_checkpoint = ddb_service.get_item(table=checkpoint_table, key_values={
            'id': event.checkpoint_id
        })
        if raw_checkpoint is None or len(raw_checkpoint) == 0:
            return {
                'statusCode': 500,
                'headers': headers,
                'error': f'checkpoint not found with id {event.checkpoint_id}'
            }

        checkpoint = CheckPoint(**raw_checkpoint)
        new_status = CheckPointStatus[event.status]
        complete_multipart_upload(checkpoint, event.multi_parts_tags)
        # if complete part failed, then no update
        ddb_service.update_item(
            table=checkpoint_table,
            key={
                'id': checkpoint.id,
            },
            field_name='checkpoint_status',
            value=new_status
        )
        return {
            'statusCode': 200,
            'headers': headers,
            'checkpoint': {
                'id': checkpoint.id,
                'type': checkpoint.checkpoint_type,
                's3_location': checkpoint.s3_location,
                'status': checkpoint.checkpoint_status.value,
                'params': checkpoint.params
            }
        }
    except Exception as e:
        logger.error(e)
        return {
            'statusCode': 500,
            'headers': headers,
            'msg': str(e)
        }
