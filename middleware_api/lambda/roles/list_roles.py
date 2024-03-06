import json
import logging
import os

from common.const import PERMISSION_ROLE_ALL, PERMISSION_ROLE_LIST
from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok
from libs.data_types import Role, PARTITION_KEYS
from libs.utils import get_permissions_by_username, get_user_roles, permissions_check, response_error

user_table = os.environ.get('MULTI_USER_TABLE')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)


# GET /roles?last_evaluated_key=xxx&limit=10&role=ROLE_NAME&filter=key:value,key:value
def handler(event, ctx):
    logger.info(json.dumps(event))
    _filter = {}

    try:
        requestor_name = permissions_check(event, [PERMISSION_ROLE_ALL, PERMISSION_ROLE_LIST])

        parameters = event['queryStringParameters']

        requestor_permissions = get_permissions_by_username(ddb_service, user_table, requestor_name)
        requestor_roles = get_user_roles(ddb_service=ddb_service, user_table_name=user_table, username=requestor_name)

        role = 0
        if parameters:
            role = parameters['role'] if 'role' in parameters and parameters['role'] else 0
        last_token = None
        if not role:
            result = ddb_service.query_items(user_table,
                                             key_values={
                                                 'kind': PARTITION_KEYS.role
                                             })

            scan_rows = result
            if type(result) is tuple:
                scan_rows = result[0]
                last_token = result[1]
        else:
            scan_rows = ddb_service.query_items(user_table, key_values={
                'kind': PARTITION_KEYS.role,
                'sort_key': role
            })

        result = []
        for row in scan_rows:
            r = Role(**(ddb_service.deserialize(row)))
            role_dto = {
                'role_name': r.sort_key,
                'creator': r.creator,
                'permissions': r.permissions
            }

            if 'role' in requestor_permissions and 'all' in requestor_permissions['role']:
                result.append(role_dto)
            elif 'role' in requestor_permissions and \
                    'list' in requestor_permissions['role'] and r.creator == requestor_name:
                result.append(role_dto)
            elif r.sort_key in requestor_roles and 'role' in requestor_permissions and \
                    'list' in requestor_permissions['role']:
                result.append(role_dto)

        data = {
            'roles': result,
            'previous_evaluated_key': 'not_applicable',
            'last_evaluated_key': last_token
        }

        return ok(data=data)
    except Exception as e:
        return response_error(e)
