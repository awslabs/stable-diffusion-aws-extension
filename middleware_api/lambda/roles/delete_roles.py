import logging
import os
from dataclasses import dataclass

import boto3

from common.response import ok, bad_request
# todo will be optimize later
from multi_users._types import PARTITION_KEYS, Default_Role

user_table = os.environ.get('MULTI_USER_TABLE')
logger = logging.getLogger('delete_roles')
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(user_table)


@dataclass
class DeleteRolesEvent:
    role_name_list: [str]


# DELETE /roles
def handler(event, ctx):
    logger.info(f'event: {event}')
    logger.info(f'ctx: {ctx}')

    event = DeleteRolesEvent(**event)

    # unique role_name_list for preventing duplicate delete
    event.role_name_list = list(set(event.role_name_list))

    if Default_Role in event.role_name_list:
        return bad_request(message='cannot delete default role')

    for role_name in event.role_name_list:
        update_users_with_role(role_name)
        table.delete_item(
            Key={
                'kind': PARTITION_KEYS.role,
                'sort_key': role_name
            }
        )

    return ok(message='roles deleted')


def update_users_with_role(role_name: str):
    users = table.query(
        KeyConditionExpression='#kind = :kind',
        ProjectionExpression='sort_key, #roles',
        FilterExpression='contains(#roles, :role_name)',
        ExpressionAttributeNames={
            '#kind': 'kind',
            '#roles': 'roles',
        },
        ExpressionAttributeValues={
            ':kind': PARTITION_KEYS.user,
            ':role_name': role_name,
        }
    )
    logger.info(f'users: {users}')

    for user in users['Items']:
        # remove role_name from roles list
        user['roles'].remove(role_name)
        # update user
        table.update_item(
            Key={
                'kind': PARTITION_KEYS.user,
                'sort_key': user['sort_key']
            },
            UpdateExpression='SET #roles = :roles',
            ExpressionAttributeNames={
                '#roles': 'roles',
            },
            ExpressionAttributeValues={
                ':roles': user['roles'],
            }
        )
