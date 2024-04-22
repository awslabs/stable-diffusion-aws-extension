import json
import logging
import os

import boto3
from aws_lambda_powertools import Tracer

from common.const import PERMISSION_TRAIN_ALL
from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok, not_found, forbidden
from libs.data_types import DatasetItem, DatasetInfo
from libs.utils import get_permissions_by_username, get_user_roles, check_user_permissions, permissions_check, \
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


@tracer.capture_lambda_handler
def handler(event, context):
    _filter = {}

    try:
        logger.info(json.dumps(event))

        requester_name = permissions_check(event, [PERMISSION_TRAIN_ALL])

        dataset_name = event['pathParameters']['id']

        dataset_info_rows = ddb_service.get_item(table=dataset_info_table, key_values={
            'dataset_name': dataset_name
        })

        if not dataset_info_rows or len(dataset_info_rows) == 0:
            return not_found(message=f'dataset {dataset_name} is not found')

        dataset_info = DatasetInfo(**dataset_info_rows)

        requestor_permissions = get_permissions_by_username(ddb_service, user_table, requester_name)
        requestor_roles = get_user_roles(ddb_service=ddb_service, user_table_name=user_table, username=requester_name)

        if not (
                (dataset_info.allowed_roles_or_users and check_user_permissions(dataset_info.allowed_roles_or_users,
                                                                                requestor_roles,
                                                                                requester_name)) or
                (not dataset_info.allowed_roles_or_users and 'user' in requestor_permissions and 'all' in
                 requestor_permissions['user'])  # legacy data for super admin
        ):
            return forbidden(message='no permission to view dataset')

        rows = ddb_service.query_items(table=dataset_item_table, key_values={
            'dataset_name': dataset_name
        })

        resp = []
        for row in rows:
            item = DatasetItem(**ddb_service.deserialize(row))
            resp = lambda_client.invoke(
                FunctionName=crop_lambda_name,
                InvocationType='Event',
                Payload=json.dumps({
                    'sort_key': item.sort_key,
                    'type': item.type,
                })
            )
            logger.info(resp)

        return ok(data={
            'dataset_name': dataset_name,
            'datasetName': dataset_info.dataset_name,
            'prefix': dataset_info.prefix,
            's3': f's3://{bucket_name}/{dataset_info.get_s3_key()}',
            'status': dataset_info.dataset_status.value,
            'timestamp': dataset_info.timestamp,
            'data': resp,
            **dataset_info.params
        }, decimal=True)
    except Exception as e:
        return response_error(e)
