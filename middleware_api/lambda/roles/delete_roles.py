import logging
import os
from dataclasses import dataclass

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok
from multi_users._types import PARTITION_KEYS

user_table = os.environ.get('MULTI_USER_TABLE')

logger = logging.getLogger('delete_roles')
logger.setLevel(logging.INFO)
ddb_service = DynamoDbUtilsService(logger=logger)


@dataclass
class DeleteRolesEvent:
    roles: [str]


# DELETE /roles
def handler(event, ctx):
    event = DeleteRolesEvent(**event)
    logger.info(f'event: {event}')

    for role in event.roles:
        logger.info(f'deleted role: {role}')
        roles_result = ddb_service.scan(table=user_table, filters={
            'kind': PARTITION_KEYS.role,
            'sort_key': role
        })
        logger.info(f'roles_result: {roles_result}')

    return ok(message='deleted roles')
