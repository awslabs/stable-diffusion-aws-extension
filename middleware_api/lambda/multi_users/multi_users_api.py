import json
from dataclasses import dataclass
import logging
import os
from typing import List, Optional

from common.ddb_service.client import DynamoDbUtilsService
from multi_users._types import User, PARTITION_KEYS, Role
from multi_users.roles_api import upsert_role
from multi_users.utils import KeyEncryptService, check_user_existence

user_table = os.environ.get('MULTI_USER_TABLE')
kms_key_id = os.environ.get('KEY_ID')

logger = logging.getLogger(__name__)
ddb_service = DynamoDbUtilsService(logger=logger)

password_encryptor = KeyEncryptService()


@dataclass
class UpsertUserEvent:
    username: str
    password: str
    creator: str
    initial: Optional[bool] = False
    roles: Optional[List[str]] = None


# POST /user
def upsert_user(raw_event, ctx):
    print(raw_event)
    event = UpsertUserEvent(**raw_event['body'])
    if event.initial:
        rolenames= ['IT Operator', 'Designer']

        ddb_service.put_items(user_table, User(
            kind=PARTITION_KEYS.user,
            sort_key=event.username,
            password=password_encryptor.encrypt(key_id=kms_key_id, text=event.password),
            roles=[rolenames[0]],
            creator=event.creator,
        ).__dict__)

        for rn in rolenames:
            role_event = {
                'role_name': rn,
                'permissions': [
                    'train:all',
                    'checkpoint:all',
                    'inference:all',
                    'sagemaker_endpoint:all',
                    'user:all'
                ],
                'creator': event.username
            }
            resp = upsert_role(role_event, {})
            if resp['statusCode'] != 200:
                return resp

        return {
            'statusCode': 200,
            'user': {
                'username': event.username,
                'roles': [rolenames[0]]
            },
            'all_roles': rolenames,
        }

    # todo: need check x-auth
    # check if creator exist
    if check_user_existence(ddb_service=ddb_service, user_table=user_table, username=event.creator):
        return {
            'statusCode': 400,
            'errMsg': f'creator {event.creator} not exist'
        }

    # check if roles exists
    roles_result = ddb_service.scan(table=user_table, filters={
        'kind': PARTITION_KEYS.role,
        'sort_key': event.roles
    })

    roles_pool = []
    for row in roles_result:
        role = Role(**ddb_service.deserialize(row))
        roles_pool.append(role.sort_key)

    for role in event.roles:
        if role not in roles_pool:
            return {
                'statusCode': 400,
                'errMsg': f'user roles "{role}" not exist'
            }

    ddb_service.put_items(user_table, User(
        kind=PARTITION_KEYS.user,
        sort_key=event.username,
        password=password_encryptor.encrypt(key_id=kms_key_id, text=event.password),
        roles=event.roles,
        creator=event.creator,
    ).__dict__)

    return {
        'statusCode': 200,
        'user': {
            'username': event.username,
            'roles': event.roles,
            'creator': event.creator,
        }
    }


# DELETE /user/{username}
def delete_user(event, ctx):
    _filter = {}
    if 'pathStringParameters' not in event:
        return {
            'statusCode': '500',
            'error': 'path parameter /user/{username}/ are needed'
        }

    username = event['pathStringParameters']['username']
    if not username or len(username) == 0:
        return {
            'statusCode': '500',
            'error': 'path parameter /user/{username}/ are needed'
        }

    scan_rows = ddb_service.query_items(user_table, key_values={
        'kind': PARTITION_KEYS.user,
        'sort_key': username
    })

    if len(scan_rows) == 0 or not scan_rows:
        return {
            'statusCode': 400,
            'errMsg': f'user {username} not found'
        }

    user = User(**(ddb_service.deserialize(scan_rows[0])))
    # todo: need to figure out what happens to user's resources
    ddb_service.delete_item(user_table, keys={
        'kind': PARTITION_KEYS.user,
        'sort_key': username
    })
    return {
        'statusCode': 200,
        'user': {
            'username': user.sort_key,
            'status': 'deleted'
        }
    }


# GET /users?last_evaluated_key=xxx&limit=10&username=USER_NAME&filter=key:value,key:value&show_password=1
def list_user(event, ctx):
    # todo: if user has no list all, we should add username to self, prevent security issue
    _filter = {}
    if 'queryStringParameters' not in event:
        return {
            'statusCode': '500',
            'error': 'query parameter status and types are needed'
        }

    parameters = event['queryStringParameters']

    limit = parameters['limit'] if 'limit' in parameters and parameters['limit'] else None
    last_evaluated_key = parameters['last_evaluated_key'] if 'last_evaluated_key' in parameters and parameters[
        'last_evaluated_key'] else None

    if last_evaluated_key and isinstance(last_evaluated_key, str):
        last_evaluated_key = json.loads(last_evaluated_key)

    show_password = parameters['show_password'] if 'show_password' in parameters and parameters['show_password'] else 0
    username = parameters['username'] if 'username' in parameters and parameters['username'] else 0

    last_token = None
    if not username:
        result = ddb_service.query_items(user_table,
                                         key_values={'kind': PARTITION_KEYS.user},
                                         last_evaluated_key=last_evaluated_key,
                                         limit=limit)

        scan_rows = result
        if type(result) is tuple:
            scan_rows = result[0]
            last_token = result[1]
    else:
        scan_rows = ddb_service.query_items(user_table, key_values={
            'kind': PARTITION_KEYS.user,
            'sort_key': username
        })

    result = []
    for row in scan_rows:
        user = User(**(ddb_service.deserialize(row)))
        result.append({
            'username': user.sort_key,
            'roles': user.roles,
            'creator': user.creator,
            'password': '*' * 8 if not show_password else password_encryptor.decrypt(
                key_id=kms_key_id, cipher_text=user.password).decode(),
        })

    return {
        'status': 200,
        'users': result,
        'previous_evaluated_key': last_evaluated_key,
        'last_evaluated_key': last_token
    }
