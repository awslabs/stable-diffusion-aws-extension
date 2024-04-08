import json
import logging
import os

from aws_lambda_powertools import Tracer

from common.const import PERMISSION_USER_ALL, PERMISSION_USER_LIST
from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok
from common.util import get_query_param
from libs.data_types import User, PARTITION_KEYS, Role
from libs.utils import KeyEncryptService, get_permissions_by_username, response_error, permissions_check

tracer = Tracer()
user_table = os.environ.get('MULTI_USER_TABLE')
kms_key_id = os.environ.get('KEY_ID')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)

password_encryptor = KeyEncryptService()


@tracer.capture_lambda_handler
def handler(event, ctx):
    # todo: if user has no list all, we should add username to self, prevent security issue
    _filter = {}

    try:
        logger.info(json.dumps(event))

        show_password = get_query_param(event, 'show_password', 0)
        username = get_query_param(event, 'username', 0)

        requester_name = permissions_check(event, [PERMISSION_USER_ALL, PERMISSION_USER_LIST])

        requester_permissions = get_permissions_by_username(ddb_service, user_table, requester_name)
        if not username:
            result = ddb_service.query_items(user_table,
                                             key_values={'kind': PARTITION_KEYS.user})

            scan_rows = result
            if type(result) is tuple:
                scan_rows = result[0]
        else:
            scan_rows = ddb_service.query_items(user_table, key_values={
                'kind': PARTITION_KEYS.user,
                'sort_key': username
            })

        # generally speaking, the number of roles is limited, so it's okay to load them into memory to process
        role_rows = ddb_service.query_items(user_table, key_values={
            'kind': PARTITION_KEYS.role
        })
        roles_permission_lookup = {}
        for role_row in role_rows:
            r = Role(**(ddb_service.deserialize(role_row)))
            roles_permission_lookup[r.sort_key] = r.permissions

        result = []
        for row in scan_rows:
            user = User(**(ddb_service.deserialize(row)))
            logger.info(f'decrypted text: {user.password}')
            password = ''
            if user.password and show_password:
                logger.info(f'decrypting for {user.sort_key}')
                password = password_encryptor.decrypt(key_id=kms_key_id, cipher_text=user.password).decode()

            user_resp = {
                'username': user.sort_key,
                'roles': user.roles,
                'creator': user.creator,
                'permissions': set(),
                'password': password,
            }

            for role in user.roles:
                if role in roles_permission_lookup:
                    user_resp['permissions'].update(roles_permission_lookup[role])
                else:
                    print(f'role {role} not found and no permission is attached')

            user_resp['permissions'] = list(user_resp['permissions'])
            user_resp['permissions'].sort()

            # only show user to requester if requester has 'user:all' permission
            # or requester has 'user:list' permission and the user is created by the requester
            if 'user' in requester_permissions and ('all' in requester_permissions['user'] or
                                                    ('list' in requester_permissions['user'] and
                                                     user.creator == requester_name)):
                result.append(user_resp)
            elif user.sort_key == requester_name:
                result.append(user_resp)

        result = sort_users(result)

        data = {
            'users': result,
            'last_evaluated_key': None
        }

        return ok(data=data)
    except Exception as e:
        return response_error(e)


def sort_users(data):
    if len(data) == 0:
        return data

    return sorted(data, key=lambda x: x['username'], reverse=True)
