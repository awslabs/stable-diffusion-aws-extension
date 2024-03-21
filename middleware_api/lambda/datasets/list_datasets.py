import json
import logging
import os

import boto3

from common.const import PERMISSION_TRAIN_ALL
from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok, bad_request, forbidden
from common.util import get_query_param
from libs.data_types import DatasetInfo
from libs.utils import get_permissions_by_username, get_user_roles, check_user_permissions, permissions_check, \
    response_error, decode_last_key, encode_last_key

dataset_info_table = os.environ.get('DATASET_INFO_TABLE')
bucket_name = os.environ.get('S3_BUCKET')
user_table = os.environ.get('MULTI_USER_TABLE')
ddb = boto3.resource('dynamodb')
table = ddb.Table(dataset_info_table)
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)


# GET /datasets
def handler(event, context):
    try:
        logger.info(json.dumps(event))
        requestor_name = permissions_check(event, [PERMISSION_TRAIN_ALL])

        exclusive_start_key = get_query_param(event, 'exclusive_start_key')
        dataset_status = get_query_param(event, 'dataset_status')
        limit = int(get_query_param(event, 'limit', 10))

        scan_kwargs = {
            'Limit': limit,
        }

        if exclusive_start_key:
            scan_kwargs['ExclusiveStartKey'] = decode_last_key(exclusive_start_key)

        requestor_permissions = get_permissions_by_username(ddb_service, user_table, requestor_name)
        requestor_roles = get_user_roles(ddb_service=ddb_service, user_table_name=user_table, username=requestor_name)
        if 'train' not in requestor_permissions or \
                ('all' not in requestor_permissions['train'] and 'list' not in requestor_permissions['train']):
            return forbidden(message='user has no permission to train')

        response = table.scan(**scan_kwargs)
        scan_rows = response.get('Items', [])
        last_evaluated_key = encode_last_key(response.get('LastEvaluatedKey'))
        if not scan_rows or len(scan_rows) == 0:
            return ok(data={'datasets': []})

        datasets = []
        for row in scan_rows:

            dataset_info = DatasetInfo(**row)

            logger.info(f'dataset_info: {dataset_info}')

            if dataset_status and dataset_info.dataset_status.value != dataset_status:
                continue

            dataset_info_dto = {
                'datasetName': dataset_info.dataset_name,
                's3': f's3://{bucket_name}/{dataset_info.get_s3_key()}',
                'status': dataset_info.dataset_status.value,
                'timestamp': dataset_info.timestamp,
                **dataset_info.params
            }

            if dataset_info.allowed_roles_or_users \
                    and check_user_permissions(dataset_info.allowed_roles_or_users, requestor_roles, requestor_name):
                datasets.append(dataset_info_dto)
            elif not dataset_info.allowed_roles_or_users and \
                    'user' in requestor_permissions and \
                    'all' in requestor_permissions['user']:
                # superuser can view the legacy data
                datasets.append(dataset_info_dto)

        datasets = sort_datasets(datasets)

        data = {
            'datasets': datasets,
            'last_evaluated_key': last_evaluated_key
        }

        return ok(data=data, decimal=True)
    except Exception as e:
        return response_error(e)


def sort_datasets(data):
    if len(data) == 0:
        return data

    return sorted(data, key=lambda x: x['timestamp'], reverse=True)
