import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime

import boto3
from aws_lambda_powertools import Tracer

from common.const import PERMISSION_TRAIN_ALL
from common.ddb_service.client import DynamoDbUtilsService
from common.excepts import NotFoundException, BadRequestException
from common.response import accepted
from datasets.crop_dataset_handler import DatasetCropItemEvent
from libs.data_types import DatasetItem, DatasetInfo
from libs.enums import DatasetStatus
from libs.utils import permissions_check, response_error

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


@tracer.capture_lambda_handler
def handler(event, context):
    try:
        logger.info(json.dumps(event))

        event_parse = DatasetCropEvent(**json.loads(event['body']))

        permissions_check(event, [PERMISSION_TRAIN_ALL])

        dataset_name = event['pathParameters']['id']

        dataset_info_rows = ddb_service.get_item(table=dataset_info_table, key_values={
            'dataset_name': dataset_name
        })

        if not dataset_info_rows or len(dataset_info_rows) == 0:
            raise NotFoundException(f'dataset {dataset_name} is not found')

        dataset_name_new = f"{dataset_name}_{event_parse.max_resolution}"

        dataset_new = ddb_service.get_item(table=dataset_info_table, key_values={'dataset_name': dataset_name_new})
        if dataset_new and len(dataset_new) > 0:
            raise BadRequestException(f'dataset {dataset_name_new} already exists')

        dataset_info = DatasetInfo(**dataset_info_rows)

        rows = ddb_service.query_items(table=dataset_item_table, key_values={
            'dataset_name': dataset_name
        })

        for row in rows:
            item = DatasetItem(**ddb_service.deserialize(row))
            old_s3_location = item.get_s3_key(dataset_info.prefix)
            payload = DatasetCropItemEvent(
                dataset_name=dataset_name_new,
                prefix=dataset_info.prefix,
                type=item.type,
                max_resolution=event_parse.max_resolution,
                name=item.name,
                user_roles=item.allowed_roles_or_users,
                old_s3_location=old_s3_location
            )
            resp = lambda_client.invoke(
                FunctionName=crop_lambda_name,
                InvocationType='Event',
                Payload=json.dumps(payload.__dict__)
            )
            logger.info(resp)

        timestamp = datetime.now().timestamp()
        new_dataset_info = DatasetInfo(
            dataset_name=dataset_name_new,
            timestamp=timestamp,
            dataset_status=DatasetStatus.Enabled,
            allowed_roles_or_users=dataset_info.allowed_roles_or_users,
            prefix=dataset_info.prefix,
            params=dataset_info.params
        )
        ddb_service.put_items(dataset_info_table, new_dataset_info.__dict__)

        return accepted(data={'dataset_name': dataset_name_new}, decimal=True)
    except Exception as e:
        return response_error(e)
