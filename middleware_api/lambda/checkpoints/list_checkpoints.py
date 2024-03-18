import json
import logging
import os

from common.const import PERMISSION_CHECKPOINT_ALL, PERMISSION_CHECKPOINT_LIST
from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok
from common.util import get_multi_query_params, get_query_param
from libs.data_types import CheckPoint, PARTITION_KEYS, Role
from libs.utils import get_user_roles, check_user_permissions, get_permissions_by_username, permissions_check, \
    response_error

checkpoint_table = os.environ.get('CHECKPOINT_TABLE')

user_table = os.environ.get('MULTI_USER_TABLE')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)


# GET /checkpoints?username=USER_NAME&types=value&status=value
def handler(event, context):
    try:
        logger.info(json.dumps(event))
        _filter = {}
        requestor_name = permissions_check(event, [PERMISSION_CHECKPOINT_ALL, PERMISSION_CHECKPOINT_LIST])
        user_roles = ['*']

        page = get_query_param(event, 'page', 1)
        per_page = get_query_param(event, 'per_page', 10)
        username = get_query_param(event, 'username', None)

        roles = get_multi_query_params(event, 'roles', default=[])

        status = get_multi_query_params(event, 'status')
        if status:
            _filter['checkpoint_status'] = status

        types = get_multi_query_params(event, 'types')
        if types:
            _filter['checkpoint_type'] = types

        if username:
            user_roles = get_user_roles(ddb_service=ddb_service, user_table_name=user_table, username=username)

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
        return response_error(e)


# todo will use query
def page_data(data, page, per_page):
    start = (page - 1) * per_page
    end = page * per_page
    return data[start:end]
