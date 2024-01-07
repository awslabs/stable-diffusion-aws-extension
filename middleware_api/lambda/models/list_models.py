import logging
import os

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok, bad_request, forbidden
from common.schemas.models import ModelCollection, ModelLink, ModelItem
from common.util import get_multi_query_params, generate_url
from libs.data_types import Model
from libs.utils import get_permissions_by_username, get_user_roles, check_user_permissions

model_table = os.environ.get('DYNAMODB_TABLE')
user_table = os.environ.get('MULTI_USER_TABLE')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)


def handler(event, context):
    _filter = {}

    types = get_multi_query_params(event, 'types')
    if types:
        _filter['model_type'] = types

    status = get_multi_query_params(event, 'status')
    if status:
        _filter['job_status'] = status

    resp = ddb_service.scan(table=model_table, filters=_filter)

    if resp is None or len(resp) == 0:
        return ok(data={'models': []})

    model_collection = ModelCollection(
        items=[],
        links=[
            ModelLink(href=generate_url(event, f'models'), rel="self", type="GET"),
            ModelLink(href=generate_url(event, f'models'), rel="create", type="POST"),
            ModelLink(href=generate_url(event, f'models'), rel="delete", type="DELETE"),
        ]
    )

    try:
        requestor_name = event['requestContext']['authorizer']['username']
        requestor_permissions = get_permissions_by_username(ddb_service, user_table, requestor_name)
        requestor_roles = get_user_roles(ddb_service=ddb_service, user_table_name=user_table, username=requestor_name)
        if 'train' not in requestor_permissions or \
                ('all' not in requestor_permissions['train'] and 'list' not in requestor_permissions['train']):
            return forbidden(message='user has no permission to train')

        for r in resp:
            model = Model(**(ddb_service.deserialize(r)))

            item = ModelItem(
                id=model.id,
                type=model.model_type,
                name=model.name,
                status=model.job_status.value,
                s3_location=model.output_s3_location,
                params=model.params,
                created=model.timestamp,
            )

            if model.allowed_roles_or_users and check_user_permissions(model.allowed_roles_or_users, requestor_roles,
                                                                       requestor_name):
                model_collection.items.append(item)
            elif not model.allowed_roles_or_users and \
                    'user' in requestor_permissions and \
                    'all' in requestor_permissions['user']:
                # superuser can view the legacy data
                model_collection.items.append(item)

        return ok(data=model_collection.dict(), decimal=True)
    except Exception as e:
        logger.error(e)
        return bad_request(message=str(e))
