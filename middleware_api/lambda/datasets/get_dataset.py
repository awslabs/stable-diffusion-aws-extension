import logging
import os

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok, not_found, forbidden
from common.schemas.datasets import DatasetInfoItem, DatasetItem as DatasetItemSchema
from common.util import generate_presign_url
from libs.data_types import DatasetItem, DatasetInfo
from libs.utils import get_permissions_by_username, get_user_roles, check_user_permissions

dataset_item_table = os.environ.get('DATASET_ITEM_TABLE')
dataset_info_table = os.environ.get('DATASET_INFO_TABLE')
bucket_name = os.environ.get('S3_BUCKET')
user_table = os.environ.get('MULTI_USER_TABLE')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)


# GET /dataset/{name}
def handler(event, context):
    _filter = {}

    dataset_name = event['pathParameters']['id']

    dataset_info_rows = ddb_service.get_item(table=dataset_info_table, key_values={
        'dataset_name': dataset_name
    })

    if not dataset_info_rows or len(dataset_info_rows) == 0:
        return not_found(message=f'dataset {dataset_name} is not found')

    dataset_info = DatasetInfo(**dataset_info_rows)

    requester_name = event['requestContext']['authorizer']['username']
    requestor_permissions = get_permissions_by_username(ddb_service, user_table, requester_name)
    requestor_roles = get_user_roles(ddb_service=ddb_service, user_table_name=user_table, username=requester_name)

    if not (
            (dataset_info.allowed_roles_or_users and check_user_permissions(dataset_info.allowed_roles_or_users,
                                                                            requestor_roles,
                                                                            requester_name)) or  # permission in dataset
            (not dataset_info.allowed_roles_or_users and 'user' in requestor_permissions and 'all' in
             requestor_permissions['user'])  # legacy data for super admin
    ):
        return forbidden(message='no permission to view dataset')

    rows = ddb_service.query_items(table=dataset_item_table, key_values={
        'dataset_name': dataset_name
    })

    dataset = DatasetItemSchema(
        name=dataset_name,
        status=dataset_info.dataset_status.value,
        s3_location=f's3://{bucket_name}/{dataset_info.get_s3_key()}',
        description=dataset_info.params.get('description'),
        items=[],
    )

    for row in rows:
        item = DatasetItem(**ddb_service.deserialize(row))
        dataset.items.append(DatasetInfoItem(
            name=item.name,
            type=item.type,
            status=item.data_status.value,
            original_file_name=item.params.get('original_file_name'),
            preview_url=generate_presign_url(bucket_name, item.get_s3_key(), expires=3600 * 24, method='get_object'),
        ))

    return ok(data=dataset.dict())
