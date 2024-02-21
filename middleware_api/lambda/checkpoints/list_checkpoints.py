import json
import logging
import os

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok, bad_request, unauthorized
from common.util import get_multi_query_params
from libs.data_types import CheckPoint, PARTITION_KEYS, Role
from libs.utils import get_user_roles, check_user_permissions, get_permissions_by_username

checkpoint_table = os.environ.get('CHECKPOINT_TABLE')

user_table = os.environ.get('MULTI_USER_TABLE')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)
MAX_WORKERS = 10


# GET /checkpoints?username=USER_NAME&types=value&status=value
def handler(event, context):
    logger.info(json.dumps(event))
    _filter = {}

    user_roles = ['*']
    username = None
    page = 1
    per_page = 10

    roles = get_multi_query_params(event, 'roles', default=[])

    status = get_multi_query_params(event, 'status')
    if status:
        _filter['checkpoint_status'] = status

    types = get_multi_query_params(event, 'types')
    if types:
        _filter['checkpoint_type'] = types

    parameters = event['queryStringParameters']
    if parameters:
        page = int(parameters['page']) if 'page' in parameters and parameters['page'] else 1
        per_page = int(parameters['per_page']) if 'per_page' in parameters and parameters['per_page'] else 10

        # todo: support multi user fetch later
        username = parameters['username'] if 'username' in parameters and parameters['username'] else None
        if username:
            user_roles = get_user_roles(ddb_service=ddb_service, user_table_name=user_table, username=username)

    if 'username' not in event['headers']:
        return unauthorized()
    requestor_name = event['headers']['username']

    try:
        requestor_permissions = get_permissions_by_username(ddb_service, user_table, requestor_name)
        requestor_created_roles_rows = ddb_service.scan(table=user_table, filters={
            'kind': PARTITION_KEYS.role,
            'creator': requestor_name
        })
        for requestor_created_roles_row in requestor_created_roles_rows:
            role = Role(**ddb_service.deserialize(requestor_created_roles_row))
            user_roles.append(role.sort_key)

        raw_ckpts = ddb_service.scan(table=checkpoint_table, filters=_filter)
        if raw_ckpts is None or len(raw_ckpts) == 0:
            data = {
                'page': page,
                'per_page': per_page,
                'pages': 0,
                'total': 0,
                'checkpoints': []
            }
            return ok(data=data)

        ckpts = []
        for r in raw_ckpts:
            ckpt = CheckPoint(**(ddb_service.deserialize(r)))

            if len(roles) > 0 and set(roles).isdisjoint(set(ckpt.allowed_roles_or_users)):
                continue

            if check_user_permissions(ckpt.allowed_roles_or_users, user_roles, username) or (
                    'user' in requestor_permissions and 'all' in requestor_permissions['user']
            ):
                ckpts.append({
                    'id': ckpt.id,
                    's3Location': ckpt.s3_location,
                    'type': ckpt.checkpoint_type,
                    'status': ckpt.checkpoint_status.value,
                    'name': ckpt.checkpoint_names,
                    'created': ckpt.timestamp,
                    'params': ckpt.params,
                    'allowed_roles_or_users': ckpt.allowed_roles_or_users
                })

        data = {
            'page': page,
            'per_page': per_page,
            'pages': int(len(ckpts) / per_page) + 1,
            'total': len(ckpts),
            'checkpoints': page_data(ckpts, page, per_page),
        }

        return ok(data=data, decimal=True)
    except Exception as e:
        logger.error(e)
        return bad_request(data=str(e))


# todo will use query
def page_data(data, page, per_page):
    start = (page - 1) * per_page
    end = page * per_page
    return data[start:end]
