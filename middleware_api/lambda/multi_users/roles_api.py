import logging
import os
from dataclasses import dataclass

from common.ddb_service.client import DynamoDbUtilsService
from multi_users._types import Role, PARTITION_KEYS
from multi_users.utils import check_user_existence

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
    if check_user_existence(ddb_service=ddb_service, user_table=user_table, username=event.creator):
        return {
            'statusCode': 400,
            'errMsg': f'creator {event.creator} not exist'
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

    limit = parameters['limit'] if 'limit' in parameters and parameters['limit'] else None
    last_evaluated_key = parameters['last_evaluated_key'] if 'last_evaluated_key' in parameters and parameters[
        'last_evaluated_key'] else None
    role = parameters['role'] if 'role' in parameters and parameters['role'] else 0
    last_token = None
    if not role:
        result = ddb_service.query_items(user_table,
                                         key_values={'kind': PARTITION_KEYS.role},
                                         last_evaluated_key=last_evaluated_key,
                                         limit=limit)

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
        result.append({
            'role_name': r.sort_key,
            'creator': r.creator,
            'permissions': r.permissions
        })

    return {
        'statusCode': 200,
        'roles': result,
        'previous_evaluated_key': last_evaluated_key,
        'last_evaluated_key': last_token
    }
