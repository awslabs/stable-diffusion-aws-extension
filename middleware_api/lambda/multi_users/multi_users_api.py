from dataclasses import dataclass
import logging
import os
import json
from typing import List, Optional

from common.ddb_service.client import DynamoDbUtilsService
from _types import User, PARTITION_KEYS, Role, Default_Role
from common.response import ok
from roles_api import upsert_role
from utils import KeyEncryptService, check_user_existence, get_permissions_by_username, get_user_by_username

user_table = os.environ.get('MULTI_USER_TABLE')
kms_key_id = os.environ.get('KEY_ID')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
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
        rolenames = [Default_Role]

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
                    'user:all',
                    'role:all'
                ],
                'creator': event.username
            }

            @dataclass
            class MockContext:
                aws_request_id: str
                from_sd_local: bool

            resp = upsert_role(role_event, MockContext(aws_request_id='', from_sd_local=True))

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

    check_permission_resp = _check_action_permission(event.creator, event.username)
    if check_permission_resp:
        return check_permission_resp

    creator_permissions = get_permissions_by_username(ddb_service, user_table, event.creator)

    # check if created roles exists
    roles_result = ddb_service.scan(table=user_table, filters={
        'kind': PARTITION_KEYS.role,
        'sort_key': event.roles
    })

    roles_pool = []
    for row in roles_result:
        role = Role(**ddb_service.deserialize(row))
        # checking if the creator has the proper permissions
        for permission in role.permissions:
            permission_parts = permission.split(':')
            resource = permission_parts[0]
            action = permission_parts[1]
            if 'all' not in creator_permissions[resource] and action not in creator_permissions[resource]:
                return {
                    'statusCode': 400,
                    'errMsg': f'creator has no permission to assign permission [{permission}] to others'
                }

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
    logger.info(f'event: {event}')
    body = json.loads(event['body'])
    user_name_list = body['user_name_list']

    requestor_name = event['requestContext']['authorizer']['username']

    for username in user_name_list:
        check_permission_resp = _check_action_permission(requestor_name, username)
        if check_permission_resp:
            return check_permission_resp

        # todo: need to figure out what happens to user's resources: models, inferences, trainings and so on
        ddb_service.delete_item(user_table, keys={
            'kind': PARTITION_KEYS.user,
            'sort_key': username
        })

    return ok(message='Users Deleted')


def _check_action_permission(creator_username, target_username):
    # check if creator exist
    if check_user_existence(ddb_service=ddb_service, user_table=user_table, username=creator_username):
        return {
            'statusCode': 400,
            'errMsg': f'creator {creator_username} not exist'
        }

    target_user = get_user_by_username(ddb_service, user_table, target_username)

    creator_permissions = get_permissions_by_username(ddb_service, user_table, creator_username)

    if 'user' not in creator_permissions or \
            ('all' not in creator_permissions['user'] and 'create' not in creator_permissions['user']):
        return {
            'statusCode': 400,
            'errMsg': f'creator {creator_username} does not have permission to manage the user'
        }

    # if the creator have no permission (not created by creator),
    # make sure the creator doesn't change the existed user (created by others)
    # and only user with 'user:all' can do update any users
    if target_user and target_user.creator != creator_username and 'all' not in creator_permissions['user']:
        return {
            'statusCode': 400,
            'errMsg': f'username {target_user.sort_key} has already exists, '
                      f'creator {creator_username} does not have permissions to change it'
        }

    if target_user and target_user.creator == creator_username and 'create' not in creator_permissions['user'] and 'all' \
            not in creator_permissions['user']:
        return {
            'statusCode': 400,
            'errMsg': f'username {target_user.sort_key} has already exists, '
                      f'creator {creator_username} does not have permissions to change it'
        }

    return None


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

    # limit = parameters['limit'] if 'limit' in parameters and parameters['limit'] else None
    # last_evaluated_key = parameters['last_evaluated_key'] if 'last_evaluated_key' in parameters and parameters[
    #     'last_evaluated_key'] else None

    # if last_evaluated_key and isinstance(last_evaluated_key, str):
    #     last_evaluated_key = json.loads(last_evaluated_key)

    show_password = parameters['show_password'] if 'show_password' in parameters and parameters['show_password'] else 0
    username = parameters['username'] if 'username' in parameters and parameters['username'] else 0

    if 'x-auth' not in event or not event['x-auth']['username']:
        return {
            'statusCode': '400',
            'error': 'no auth provided'
        }

    requester_name = event['x-auth']['username']
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
        user_resp = {
            'username': user.sort_key,
            'roles': user.roles,
            'creator': user.creator,
            'permissions': set(),
            'password': '*' * 8 if not show_password else password_encryptor.decrypt(
                key_id=kms_key_id, cipher_text=user.password).decode(),
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

    return {
        'status': 200,
        'users': result,
        'previous_evaluated_key': "not_applicable",
        'last_evaluated_key': "not_applicable"
    }
