import json
import logging
import os
from dataclasses import dataclass
from typing import List, Optional

from common.const import PERMISSION_USER_ALL
from common.ddb_service.client import DynamoDbUtilsService
from common.response import bad_request, created, forbidden
from libs.data_types import User, PARTITION_KEYS, Role, Default_Role
from libs.utils import KeyEncryptService, check_user_existence, get_permissions_by_username, get_user_by_username, \
    permissions_check, response_error
from roles.create_role import handler as upsert_role

user_table = os.environ.get('MULTI_USER_TABLE')
kms_key_id = os.environ.get('KEY_ID')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)

password_encryptor = KeyEncryptService()


@dataclass
class UpsertUserEvent:
    username: str
    password: str
    initial: Optional[bool] = False
    roles: Optional[List[str]] = None
    # todo: will be removed
    creator: str = ""


def handler(raw_event, ctx):
    try:
        logger.info(json.dumps(raw_event))
        event = UpsertUserEvent(**json.loads(raw_event['body']))

        if event.initial:
            username = raw_event['headers']['username']
        else:
            username = permissions_check(raw_event, [PERMISSION_USER_ALL])

        if event.initial:
            role_names = [Default_Role]

            ddb_service.put_items(user_table, User(
                kind=PARTITION_KEYS.user,
                sort_key=event.username,
                password=password_encryptor.encrypt(key_id=kms_key_id, text=event.password),
                roles=[role_names[0]],
                creator=username,
            ).__dict__)

            for rn in role_names:
                role_event = {
                    'role_name': rn,
                    'initial': event.initial,
                    'permissions': [
                        'train:all',
                        'checkpoint:all',
                        'inference:all',
                        'sagemaker_endpoint:all',
                        'user:all',
                        'role:all'
                    ],
                }

                @dataclass
                class MockContext:
                    aws_request_id: str
                    from_sd_local: bool

                # todo will be remove, not use api
                create_role_event = {
                    'body': json.dumps(role_event),
                    'headers': raw_event['headers'],
                }
                resp = upsert_role(create_role_event, MockContext(aws_request_id='', from_sd_local=True))

                if resp['statusCode'] != 201:
                    return resp

            data = {
                'user': {
                    'username': event.username,
                    'roles': [role_names[0]]
                },
                'all_roles': role_names,
            }

            return created(data=data)

        check_permission_resp = _check_action_permission(username, event.username)
        if check_permission_resp:
            return check_permission_resp

        creator_permissions = get_permissions_by_username(ddb_service, user_table, username)

        # check if created roles exist
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
                    return forbidden(message=f'creator has no permission to assign permission [{permission}] to others')

            roles_pool.append(role.sort_key)

        for role in event.roles:
            if role not in roles_pool:
                return bad_request(message=f'user roles "{role}" not exist')

        ddb_service.put_items(user_table, User(
            kind=PARTITION_KEYS.user,
            sort_key=event.username,
            password=password_encryptor.encrypt(key_id=kms_key_id, text=event.password),
            roles=event.roles,
            creator=username,
        ).__dict__)

        return created()
    except Exception as e:
        return response_error(e)


def _check_action_permission(creator_username, target_username):
    # check if the creator exists
    if check_user_existence(ddb_service=ddb_service, user_table=user_table, username=creator_username):
        return bad_request(message=f'creator {creator_username} not exist')

    target_user = get_user_by_username(ddb_service, user_table, target_username)

    creator_permissions = get_permissions_by_username(ddb_service, user_table, creator_username)

    if 'user' not in creator_permissions or \
            ('all' not in creator_permissions['user'] and 'create' not in creator_permissions['user']):
        return forbidden(message=f'creator {creator_username} does not have permission to manage the user')

    # if the creator has no permission (not created by creator),
    # make sure the creator doesn't change the existed user (created by others)
    # and only user with 'user:all' can do update any users
    if target_user and target_user.creator != creator_username and 'all' not in creator_permissions['user']:
        return bad_request(message=f'username {target_user.sort_key} has already exists, '
                                   f'creator {creator_username} does not have permissions to change it')

    if target_user and target_user.creator == creator_username and 'create' not in creator_permissions['user'] and 'all' \
            not in creator_permissions['user']:
        return bad_request(
            message=f'username {target_user.sort_key} has already exists, '
                    f'creator {creator_username} does not have permissions to change it')

    return None
