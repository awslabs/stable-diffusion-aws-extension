import json
import logging
import os
from dataclasses import dataclass

import boto3

from common.response import no_content, bad_request
from libs.data_types import PARTITION_KEYS, Default_Role

logger = logging.getLogger('delete_roles')
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
user_table = dynamodb.Table(os.environ.get('MULTI_USER_TABLE'))


@dataclass
class DeleteRolesEvent:
    role_name_list: [str]


def handler(event, ctx):
    logger.info(f'event: {event}')
    logger.info(f'ctx: {ctx}')

    body = DeleteRolesEvent(**json.loads(event['body']))

    # unique role_name_list for preventing duplicate delete
    role_name_list = list(set(body.role_name_list))

    if Default_Role in role_name_list:
        return bad_request(message='cannot delete default role')

    for role_name in role_name_list:
        update_users_with_role(role_name)
        user_table.delete_item(
            Key={
                'kind': PARTITION_KEYS.role,
                'sort_key': role_name
            }
        )

    return no_content(message='roles deleted')


def update_users_with_role(role_name: str):
    users = user_table.query(
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
        user_table.update_item(
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
