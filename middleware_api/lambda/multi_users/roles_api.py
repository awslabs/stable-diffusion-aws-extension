import logging
import os
from dataclasses import dataclass

from common.ddb_service.client import DynamoDbUtilsService
from _types import Role, PARTITION_KEYS
from utils import check_user_existence, get_permissions_by_username, get_user_roles

user_table = os.environ.get('MULTI_USER_TABLE')

logger = logging.getLogger('roles_api')
ddb_service = DynamoDbUtilsService(logger=logger)


@dataclass
class UpsertRoleEvent:
    role_name: str
    permissions: [str]
    creator: str


# POST /role
def upsert_role(raw_event, ctx):
    event = UpsertRoleEvent(**raw_event)

    # check if creator exist
    # if check_user_existence(ddb_service=ddb_service, user_table=user_table, username=event.creator):
    #     return {
    #         'statusCode': 400,
    #         'errMsg': f'creator {event.creator} not exist'
    #     }

    if not ctx or 'from_sd_local' not in vars(ctx):
        # should check the creator permission contains role:all
        creator_permissions = get_permissions_by_username(ddb_service, user_table, event.creator)
        if 'role' not in creator_permissions or \
                ('all' not in creator_permissions['role'] and 'create' not in creator_permissions['role']):
            return {
                'statusCode': 400,
                'errMsg': f'creator {event.creator} not have permission to create role'
            }

        if 'all' not in creator_permissions['role']:
            target_role = _get_role_by_name(event.role_name)
            if target_role and target_role.creator != event.creator:
                return {
                    'statusCode': 400,
                    'errMsg': f'creator {event.creator} not have permission to update role {target_role.sort_key}'
                }

            for permission_str in event.permissions:
                permission_parts = permission_str.split(':')
                resource = permission_parts[0]
                action = permission_parts[1]
                if resource not in creator_permissions or \
                        ('all' not in creator_permissions[resource] and action not in creator_permissions[resource]):
                    return {
                        'statusCode': 400,
                        'errMsg': f'creator {event.creator} have not permission '
                                  f'to create role with permission: [{permission_str}]'
                    }

    if not ctx or 'from_sd_local' not in vars(ctx):
        # should check the creator permission contains role:all
        creator_permissions = get_permissions_by_username(ddb_service, user_table, event.creator)
        if 'role' not in creator_permissions or \
                ('all' not in creator_permissions['role'] and 'create' not in creator_permissions['role']):
            return {
                'statusCode': 400,
                'errMsg': f'creator {event.creator} not have permission to create role'
            }

        if 'all' not in creator_permissions['role']:
            target_role = _get_role_by_name(event.role_name)
            if target_role and target_role.creator != event.creator:
                return {
                    'statusCode': 400,
                    'errMsg': f'creator {event.creator} not have permission to update role {target_role.sort_key}'
                }

            for permission_str in event.permissions:
                permission_parts = permission_str.split(':')
                resource = permission_parts[0]
                action = permission_parts[1]
                if resource not in creator_permissions or \
                        ('all' not in creator_permissions[resource] and action not in creator_permissions[resource]):
                    return {
                        'statusCode': 400,
                        'errMsg': f'creator {event.creator} have not permission '
                                  f'to create role with permission: [{permission_str}]'
                    }

    ddb_service.put_items(user_table, Role(
        kind=PARTITION_KEYS.role,
        sort_key=event.role_name,
        permissions=event.permissions,
        creator=event.creator,
    ).__dict__)

    return {
        'statusCode': 200,
        'role': {
            'role_name':  event.role_name,
            'permissions': event.permissions,
            'creator': event.creator,
        }
    }


# GET /roles?last_evaluated_key=xxx&limit=10&role=ROLE_NAME&filter=key:value,key:value
def list_roles(event, ctx):
    _filter = {}
    if 'queryStringParameters' not in event:
        return {
            'statusCode': '500',
            'error': 'query parameter status and types are needed'
        }

    parameters = event['queryStringParameters']
    if 'x-auth' not in event or not event['x-auth']['username']:
        return {
            'statusCode': '400',
            'error': 'no auth provided'
        }

    requestor_name = event['x-auth']['username']
    requestor_permissions = get_permissions_by_username(ddb_service, user_table, requestor_name)
    requestor_roles = get_user_roles(ddb_service=ddb_service, user_table_name=user_table, username=requestor_name)

    role = parameters['role'] if 'role' in parameters and parameters['role'] else 0
    last_token = None
    if not role:
        result = ddb_service.query_items(user_table,
                                         key_values={
                                             'kind': PARTITION_KEYS.role
                                         })

        scan_rows = result
        if type(result) is tuple:
            scan_rows = result[0]
            last_token = result[1]
    else:
        scan_rows = ddb_service.query_items(user_table, key_values={
            'kind': PARTITION_KEYS.role,
            'sort_key': role
        })

    result = []
    for row in scan_rows:
        r = Role(**(ddb_service.deserialize(row)))
        role_dto = {
            'role_name': r.sort_key,
            'creator': r.creator,
            'permissions': r.permissions
        }

        if 'role' in requestor_permissions and 'all' in requestor_permissions['role']:
            result.append(role_dto)
        elif 'role' in requestor_permissions and \
                'list' in requestor_permissions['role'] and r.creator == requestor_name:
            result.append(role_dto)
        elif r.sort_key in requestor_roles and 'role' in requestor_permissions and \
                'list' in requestor_permissions['role']:
            result.append(role_dto)
    return {
        'statusCode': 200,
        'roles': result,
        'previous_evaluated_key': 'not_applicable',
        'last_evaluated_key': last_token
    }


def _get_role_by_name(role_name):
    role_raw = ddb_service.query_items(table=user_table, key_values={
        'kind': PARTITION_KEYS.role,
        'sort_key': role_name,
    })

    if not role_raw or len(role_raw) == 0:
        return None

    return Role(**(ddb_service.deserialize(role_raw)))
