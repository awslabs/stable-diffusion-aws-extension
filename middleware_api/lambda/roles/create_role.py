import json
import logging
import os
from dataclasses import dataclass

from common.ddb_service.client import DynamoDbUtilsService
from common.response import bad_request, created
from libs.data_types import Role, PARTITION_KEYS
from libs.utils import check_user_existence, get_permissions_by_username

user_table = os.environ.get('MULTI_USER_TABLE')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ddb_service = DynamoDbUtilsService(logger=logger)


@dataclass
class UpsertRoleEvent:
    role_name: str
    permissions: [str]
    creator: str


def handler(raw_event, ctx):
    event = UpsertRoleEvent(**json.loads(raw_event['body']))

    # check if creator exist
    if check_user_existence(ddb_service=ddb_service, user_table=user_table, username=event.creator):
        return bad_request(message=f'creator {event.creator} not exist')

    if not ctx or 'from_sd_local' not in vars(ctx):
        # should check the creator permission contains role:all
        creator_permissions = get_permissions_by_username(ddb_service, user_table, event.creator)
        if 'role' not in creator_permissions or \
                ('all' not in creator_permissions['role'] and 'create' not in creator_permissions['role']):
            return bad_request(message=f'creator {event.creator} not have permission to create role')

        if 'all' not in creator_permissions['role']:
            target_role = _get_role_by_name(event.role_name)
            if target_role and target_role.creator != event.creator:
                return bad_request(
                    message=f'creator {event.creator} not have permission to update role {target_role.sort_key}')

            for permission_str in event.permissions:
                permission_parts = permission_str.split(':')
                resource = permission_parts[0]
                action = permission_parts[1]
                if resource not in creator_permissions or \
                        ('all' not in creator_permissions[resource] and action not in creator_permissions[resource]):
                    return bad_request(
                        message=f'creator {event.creator} have not permission to create role with permission: [{permission_str}]')

    ddb_service.put_items(user_table, Role(
        kind=PARTITION_KEYS.role,
        sort_key=event.role_name,
        permissions=event.permissions,
        creator=event.creator,
    ).__dict__)

    data = {
        'role_name': event.role_name,
        'permissions': event.permissions,
        'creator': event.creator,
    }

    return created(message='role created', data=data)
