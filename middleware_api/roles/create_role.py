import json
import logging
import os
from dataclasses import dataclass
from typing import Optional

from aws_lambda_powertools import Tracer

from common.const import PERMISSION_ROLE_ALL, PERMISSION_ROLE_CREATE
from common.ddb_service.client import DynamoDbUtilsService
from common.response import bad_request, created
from libs.data_types import Role, PARTITION_KEYS
from libs.utils import get_permissions_by_username, permissions_check, response_error, get_user_name

tracer = Tracer()
user_table = os.environ.get('MULTI_USER_TABLE')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)


@dataclass
class UpsertRoleEvent:
    role_name: str
    permissions: [str]
    initial: Optional[bool] = False
    # todo: will be removed
    creator: str = ""


@tracer.capture_lambda_handler
def handler(raw_event, ctx):
    try:
        logger.info(json.dumps(raw_event))
        event = UpsertRoleEvent(**json.loads(raw_event['body']))

        if event.initial:
            username = get_user_name(raw_event)
        else:
            username = permissions_check(raw_event, [PERMISSION_ROLE_ALL, PERMISSION_ROLE_CREATE])

        if not ctx or 'from_sd_local' not in vars(ctx):
            # should check the creator permission contains role:all
            creator_permissions = get_permissions_by_username(ddb_service, user_table, username)

            if 'all' not in creator_permissions['role']:
                target_role = _get_role_by_name(event.role_name)
                if target_role and target_role.creator != username:
                    return bad_request(
                        message=f'creator {username} not have permission to update role {target_role.sort_key}')

                for permission_str in event.permissions:
                    permission_parts = permission_str.split(':')
                    resource = permission_parts[0]
                    action = permission_parts[1]
                    if resource not in creator_permissions or \
                            ('all' not in creator_permissions[resource] and action not in creator_permissions[
                                resource]):
                        return bad_request(
                            message=f'creator {username} have not permission to create role with permission: [{permission_str}]')

        ddb_service.put_items(user_table, Role(
            kind=PARTITION_KEYS.role,
            sort_key=event.role_name,
            permissions=event.permissions,
            creator=username,
        ).__dict__)

        return created(message='role created')
    except Exception as e:
        return response_error(e)


def _get_role_by_name(role_name):
    role_raw = ddb_service.query_items(table=user_table, key_values={
        'kind': PARTITION_KEYS.role,
        'sort_key': role_name,
    })

    if not role_raw or len(role_raw) == 0:
        return None

    return Role(**(ddb_service.deserialize(role_raw)))
