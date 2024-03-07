import json
import logging
import os

from common.const import PERMISSION_TRAIN_ALL
from libs.data_types import DatasetInfo
from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok, bad_request, unauthorized
from libs.utils import get_permissions_by_username, get_user_roles, check_user_permissions, permissions_check, \
    response_error

dataset_item_table = os.environ.get('DATASET_ITEM_TABLE')
dataset_info_table = os.environ.get('DATASET_INFO_TABLE')
bucket_name = os.environ.get('S3_BUCKET')
user_table = os.environ.get('MULTI_USER_TABLE')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)


# GET /datasets
def handler(event, context):
    _filter = {}

    parameters = event['queryStringParameters']
    if parameters:
        if 'dataset_status' in parameters and len(parameters['dataset_status']) > 0:
            _filter['dataset_status'] = parameters['dataset_status']

    try:
        logger.info(json.dumps(event))
        requestor_name = permissions_check(event, [PERMISSION_TRAIN_ALL])

        requestor_permissions = get_permissions_by_username(ddb_service, user_table, requestor_name)
        requestor_roles = get_user_roles(ddb_service=ddb_service, user_table_name=user_table, username=requestor_name)
        if 'train' not in requestor_permissions or \
                ('all' not in requestor_permissions['train'] and 'list' not in requestor_permissions['train']):
            return bad_request(message='user has no permission to train')

        resp = ddb_service.scan(table=dataset_info_table, filters=_filter)
        if not resp or len(resp) == 0:
            return ok(data={'datasets': []})

        datasets = []
        for tr in resp:
            dataset_info = DatasetInfo(**(ddb_service.deserialize(tr)))
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

        return ok(data={'datasets': datasets}, decimal=True)
    except Exception as e:
        return response_error(e)
