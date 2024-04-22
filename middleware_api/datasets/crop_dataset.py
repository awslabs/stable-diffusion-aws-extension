import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime

import boto3
from aws_lambda_powertools import Tracer

from common.const import PERMISSION_TRAIN_ALL
from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok, not_found
from libs.data_types import DatasetItem, DatasetInfo
from libs.enums import DatasetStatus
from libs.utils import get_user_roles, permissions_check, \
    response_error

tracer = Tracer()
dataset_item_table = os.environ.get('DATASET_ITEM_TABLE')
dataset_info_table = os.environ.get('DATASET_INFO_TABLE')
bucket_name = os.environ.get('S3_BUCKET_NAME')
user_table = os.environ.get('MULTI_USER_TABLE')
crop_lambda_name = os.environ.get('CROP_LAMBDA_NAME')
lambda_client = boto3.client('lambda')
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)


@dataclass
class DatasetCropEvent:
    max_resolution: str
    prefix: str = None


@tracer.capture_lambda_handler
def handler(event, context):
    _filter = {}

    try:
        logger.info(json.dumps(event))

        event_parse = DatasetCropEvent(**json.loads(event['body']))

        username = permissions_check(event, [PERMISSION_TRAIN_ALL])

        dataset_name = event['pathParameters']['id']

        dataset_info_rows = ddb_service.get_item(table=dataset_info_table, key_values={
            'dataset_name': dataset_name
        })

        if not dataset_info_rows or len(dataset_info_rows) == 0:
            return not_found(message=f'dataset {dataset_name} is not found')

        dataset_info = DatasetInfo(**dataset_info_rows)

        rows = ddb_service.query_items(table=dataset_item_table, key_values={
            'dataset_name': dataset_name
        })

        dataset_name_new = f"{dataset_name}_{event_parse.max_resolution}"

        user_roles = get_user_roles(ddb_service, user_table, username)

        for row in rows:
            item = DatasetItem(**ddb_service.deserialize(row))
            s3_location = item.get_s3_key(dataset_info.prefix)
            resp = lambda_client.invoke(
                FunctionName=crop_lambda_name,
                InvocationType='Event',
                Payload=json.dumps({
                    'dataset_name': dataset_name_new,
                    'src_img_s3_path': s3_location,
                    'max_resolution': event_parse.max_resolution,
                    'user_roles': user_roles,
                })
            )
            logger.info(resp)

        timestamp = datetime.now().timestamp()
        new_dataset_info = DatasetInfo(
            dataset_name=dataset_name_new,
            timestamp=timestamp,
            dataset_status=DatasetStatus.Initialed,
            allowed_roles_or_users=user_roles,
            prefix=event.prefix,
        )

        ddb_service.batch_put_items({
            dataset_info_table: [new_dataset_info.__dict__],
        })

        return ok(data={
            'dataset_name': dataset_name_new,
        }, decimal=True)
    except Exception as e:
        return response_error(e)
