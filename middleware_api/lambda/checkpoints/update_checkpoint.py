import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict

import boto3

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok, internal_server_error, not_found, bad_request
from libs.common_tools import complete_multipart_upload
from libs.data_types import CheckPoint, CheckPointStatus

checkpoint_table = os.environ.get('CHECKPOINT_TABLE')
bucket_name = os.environ.get('S3_BUCKET')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ddb_service = DynamoDbUtilsService(logger=logger)
s3_client = boto3.client('s3')

headers = {
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}


@dataclass
class UpdateCheckPointEvent:
    name: str = None
    status: str = None
    multi_parts_tags: Dict[str, Any] = None


# PUT /checkpoints/{id}
def handler(raw_event, context):
    event = UpdateCheckPointEvent(**json.loads(raw_event['body']))
    checkpoint_id = raw_event['pathParameters']['id']

    try:
        raw_checkpoint = ddb_service.get_item(table=checkpoint_table, key_values={
            'id': checkpoint_id
        })
        if raw_checkpoint is None or len(raw_checkpoint) == 0:
            return not_found(
                message=f'checkpoint not found with id {checkpoint_id}',
                headers=headers
            )

        checkpoint = CheckPoint(**raw_checkpoint)
        if event.status:
            return update_status(event, checkpoint)
        if event.name:
            return update_name(event, checkpoint)
        return ok(headers=headers)
    except Exception as e:
        logger.error(e)
        return internal_server_error(headers=headers, message=str(e))


def update_status(event: UpdateCheckPointEvent, checkpoint: CheckPoint):
    if event.multi_parts_tags is None or len(event.multi_parts_tags) == 0:
        return bad_request(message='multi parts tags is empty', headers=headers)
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
    data = {
        'checkpoint': {
            'id': checkpoint.id,
            'type': checkpoint.checkpoint_type,
            's3_location': checkpoint.s3_location,
            'status': checkpoint.checkpoint_status.value,
            'params': checkpoint.params
        }
    }
    return ok(data=data, headers=headers)


def update_name(event: UpdateCheckPointEvent, checkpoint: CheckPoint):
    if checkpoint.checkpoint_status != CheckPointStatus.Active:
        return bad_request(message='checkpoint status is not active', headers=headers)

    old_name = checkpoint.checkpoint_names[0]
    s3_path = checkpoint.s3_location.replace(f's3://{bucket_name}/', '')

    rename_s3_object(f"{s3_path}/{old_name}", f"{s3_path}/{event.name}")

    ddb_service.update_item(
        table=checkpoint_table,
        key={
            'id': checkpoint.id,
        },
        field_name='checkpoint_names',
        value=[
            event.name
        ]
    )

    return ok(headers=headers)


def rename_s3_object(old_key, new_key):
    # Copy the object to the new key
    s3_client.copy_object(Bucket=bucket_name, CopySource={'Bucket': bucket_name, 'Key': old_key}, Key=new_key)

    # Delete the original object
    s3_client.delete_object(Bucket=bucket_name, Key=old_key)
