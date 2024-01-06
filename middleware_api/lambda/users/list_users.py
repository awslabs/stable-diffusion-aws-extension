import json
import logging
import os

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok
from common.schemas.users import UserCollection, UserLink, UserItem
from common.util import generate_url
from libs.data_types import User, PARTITION_KEYS, Role
from libs.utils import KeyEncryptService, get_permissions_by_username

user_table = os.environ.get('MULTI_USER_TABLE')
kms_key_id = os.environ.get('KEY_ID')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)

password_encryptor = KeyEncryptService()


def handler(event, ctx):
    logger.info(json.dumps(event))
    # todo: if user has no list all, we should add username to self, prevent security issue
    _filter = {}

    parameters = event['queryStringParameters']

    show_password = 0
    username = 0
    if parameters:
        show_password = parameters['show_password'] if 'show_password' in parameters and parameters[
            'show_password'] else 0
        username = parameters['username'] if 'username' in parameters and parameters['username'] else 0

    requester_name = event['requestContext']['authorizer']['username']
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

    user_collection = UserCollection(
        items=[],
        links=[
            UserLink(href=generate_url(event, f'users'), rel="self", type="GET"),
            UserLink(href=generate_url(event, f'users'), rel="create", type="POST"),
            UserLink(href=generate_url(event, f'users'), rel="delete", type="DELETE"),
        ]
    )

    for row in scan_rows:
        user = User(**(ddb_service.deserialize(row)))

        item = UserItem(
            name=user.sort_key,
            creator=user.creator,
            roles=user.roles,
            permissions=[],
        )

        for role in user.roles:
            if role in roles_permission_lookup:
                item.permissions = roles_permission_lookup[role]
            else:
                print(f'role {role} not found and no permission is attached')

        # only show user to requester if requester has 'user:all' permission
        # or requester has 'user:list' permission and the user is created by the requester
        if 'user' in requester_permissions and ('all' in requester_permissions['user'] or
                                                ('list' in requester_permissions['user'] and
                                                 user.creator == requester_name)):
            user_collection.items.append(item)
        elif user.sort_key == requester_name:
            user_collection.items.append(item)

    user_collection.previous_evaluated_key = "not_applicable"
    user_collection.last_evaluated_key = "not_applicable"

    return ok(data=user_collection.dict())
