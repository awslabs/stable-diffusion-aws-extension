import json
import logging
import os

import boto3
from aws_lambda_powertools import Tracer

from common.const import PERMISSION_ENDPOINT_ALL, PERMISSION_ENDPOINT_LIST
from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok
from common.util import get_query_param
from libs.data_types import EndpointDeploymentJob, PARTITION_KEYS, Role
from libs.enums import EndpointStatus
from libs.utils import get_user_roles, check_user_permissions, get_permissions_by_username, permissions_check, \
    response_error, decode_last_key, encode_last_key

tracer = Tracer()
sagemaker_endpoint_table = os.environ.get('ENDPOINT_TABLE_NAME')
user_table = os.environ.get('MULTI_USER_TABLE')
ddb = boto3.resource('dynamodb')
table = ddb.Table(sagemaker_endpoint_table)
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)


# GET /endpoints?name=SageMaker_Endpoint_Name&username=&filter=key:value,key:value
@tracer.capture_lambda_handler
def handler(event, ctx):
    _filter = {}

    try:
        logger.info(json.dumps(event))
        requestor_name = permissions_check(event, [PERMISSION_ENDPOINT_ALL, PERMISSION_ENDPOINT_LIST])

        exclusive_start_key = get_query_param(event, 'exclusive_start_key')
        limit = int(get_query_param(event, 'limit', 10))
        last_evaluated_key = ''

        scan_kwargs = {
            'Limit': limit,
        }

        if exclusive_start_key:
            scan_kwargs['ExclusiveStartKey'] = decode_last_key(exclusive_start_key)

        endpoint_deployment_job_id = get_query_param(event, 'endpointDeploymentJobId', None)
        username = get_query_param(event, 'username', None)

        if endpoint_deployment_job_id:
            scan_rows = ddb_service.query_items(sagemaker_endpoint_table,
                                                key_values={'EndpointDeploymentJobId': endpoint_deployment_job_id},
                                                )
        else:
            response = table.scan(**scan_kwargs)
            scan_rows = response.get('Items', [])
            last_evaluated_key = encode_last_key(response.get('LastEvaluatedKey'))

        results = []
        user_roles = []

        if username:
            user_roles = get_user_roles(ddb_service=ddb_service, user_table_name=user_table, username=username)

        requestor_permissions = get_permissions_by_username(ddb_service, user_table, requestor_name)
        requestor_created_roles_rows = ddb_service.scan(table=user_table, filters={
            'kind': PARTITION_KEYS.role,
            'creator': requestor_name
        })
        for requestor_created_roles_row in requestor_created_roles_rows:
            role = Role(**ddb_service.deserialize(requestor_created_roles_row))
            user_roles.append(role.sort_key)

        for row in scan_rows:
            # Compatible with fields used in older data, must be 'deleted'
            if 'status' in row and 'S' in row['status'] and row['status']['S'] == 'deleted':
                row['endpoint_status']['S'] = EndpointStatus.DELETED.value

            endpoint = EndpointDeploymentJob(**row)
            if 'sagemaker_endpoint' in requestor_permissions and \
                    'list' in requestor_permissions['sagemaker_endpoint'] and \
                    endpoint.owner_group_or_role and \
                    username and check_user_permissions(endpoint.owner_group_or_role, user_roles, username):
                results.append(endpoint.__dict__)
            elif 'sagemaker_endpoint' in requestor_permissions and 'all' in requestor_permissions['sagemaker_endpoint']:
                results.append(endpoint.__dict__)

        # Old data may never update the count of instances
        for result in results:
            if 'current_instance_count' not in result:
                result['current_instance_count'] = 'N/A'

        results = sort_endpoints(results)

        data = {
            'endpoints': results,
            'last_evaluated_key': last_evaluated_key
        }

        return ok(data=data, decimal=True)
    except Exception as e:
        return response_error(e)


def sort_endpoints(data):
    if len(data) == 0:
        return data

    return sorted(data, key=lambda x: x['startTime'], reverse=True)
