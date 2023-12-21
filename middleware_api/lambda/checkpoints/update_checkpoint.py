import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok, bad_request, internal_server_error
from lib._types import CheckPoint, CheckPointStatus
from lib.common_tools import complete_multipart_upload

checkpoint_table = os.environ.get('CHECKPOINT_TABLE')
bucket_name = os.environ.get('S3_BUCKET')
checkpoint_type = ["Stable-diffusion", "embeddings", "Lora", "hypernetworks", "ControlNet", "VAE"]
user_table = os.environ.get('MULTI_USER_TABLE')
CN_MODEL_EXTS = [".pt", ".pth", ".ckpt", ".safetensors", ".yaml"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ddb_service = DynamoDbUtilsService(logger=logger)
MAX_WORKERS = 10


@dataclass
class UpdateCheckPointEvent:
    status: str
    multi_parts_tags: Dict[str, Any]


# PUT /checkpoints/{id}
def handler(raw_event, context):
    event = UpdateCheckPointEvent(**json.loads(raw_event['body']))
    checkpoint_id = raw_event['pathParameters']['id']
    headers = {
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
    }
    try:
        raw_checkpoint = ddb_service.get_item(table=checkpoint_table, key_values={
            'id': checkpoint_id
        })
        if raw_checkpoint is None or len(raw_checkpoint) == 0:
            return bad_request(
                message=f'checkpoint not found with id {checkpoint_id}',
                headers=headers
            )

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
    except Exception as e:
        logger.error(e)
        return internal_server_error(headers=headers, message=str(e))
