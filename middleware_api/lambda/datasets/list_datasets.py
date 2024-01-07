import logging
import os

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok, bad_request, forbidden
from common.schemas.datasets import DatasetCollection, DatasetItem, DatasetLink
from common.util import generate_url
from libs.data_types import DatasetInfo
from libs.utils import get_permissions_by_username, get_user_roles, check_user_permissions

dataset_info_table = os.environ.get('DATASET_INFO_TABLE')
bucket_name = os.environ.get('S3_BUCKET')
user_table = os.environ.get('MULTI_USER_TABLE')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)


# GET /datasets
def handler(event, context):
    _filter = {}

    dataset_collection = DatasetCollection(
        items=[],
        links=[
            DatasetLink(href=generate_url(event, f'datasets'), rel="self", type="GET"),
            DatasetLink(href=generate_url(event, f'datasets'), rel="create", type="POST"),
            DatasetLink(href=generate_url(event, f'datasets'), rel="delete", type="DELETE"),
        ]
    )

    parameters = event['queryStringParameters']
    if parameters:
        if 'dataset_status' in parameters and len(parameters['dataset_status']) > 0:
            _filter['dataset_status'] = parameters['dataset_status']

    try:
        requestor_name = event['requestContext']['authorizer']['username']
        requestor_permissions = get_permissions_by_username(ddb_service, user_table, requestor_name)
        requestor_roles = get_user_roles(ddb_service=ddb_service, user_table_name=user_table, username=requestor_name)
        if 'train' not in requestor_permissions or \
                ('all' not in requestor_permissions['train'] and 'list' not in requestor_permissions['train']):
            return forbidden(message='user has no permission to train')

        resp = ddb_service.scan(table=dataset_info_table, filters=_filter)
        if not resp or len(resp) == 0:
            return ok(data=dataset_collection.dict())

        for tr in resp:
            dataset_info = DatasetInfo(**(ddb_service.deserialize(tr)))

            dataset_info_dto = DatasetItem(
                name=dataset_info.dataset_name,
                s3_location=f's3://{bucket_name}/{dataset_info.get_s3_key()}',
                timestamp=dataset_info.timestamp,
                status=dataset_info.dataset_status.value,
                description=dataset_info.params.get('description', ''),
            )

            if dataset_info.allowed_roles_or_users \
                    and check_user_permissions(dataset_info.allowed_roles_or_users, requestor_roles, requestor_name):
                dataset_collection.items.append(dataset_info_dto)
            elif not dataset_info.allowed_roles_or_users and \
                    'user' in requestor_permissions and \
                    'all' in requestor_permissions['user']:
                # superuser can view the legacy data
                dataset_collection.items.append(dataset_info_dto)

        return ok(data=dataset_collection.dict())
    except Exception as e:
        logger.error(e)
        return bad_request(message=str(e))
