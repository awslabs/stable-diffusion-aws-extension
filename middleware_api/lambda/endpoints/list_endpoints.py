import logging
import os

from common.ddb_service.client import DynamoDbUtilsService
from libs.enums import EndpointStatus
from common.response import ok, bad_request, unauthorized
from libs.data_types import EndpointDeploymentJob, PARTITION_KEYS, Role
from libs.utils import get_user_roles, check_user_permissions, get_permissions_by_username

sagemaker_endpoint_table = os.environ.get('DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME')
user_table = os.environ.get('MULTI_USER_TABLE')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)


# GET /endpoints?name=SageMaker_Endpoint_Name&username=&filter=key:value,key:value
def handler(event, ctx):
    _filter = {}

    endpoint_deployment_job_id = None
    username = None
    parameters = event['queryStringParameters']
    if parameters:
        endpoint_deployment_job_id = parameters[
            'endpointDeploymentJobId'] if 'endpointDeploymentJobId' in parameters and \
                                          parameters[
                                              'endpointDeploymentJobId'] else None
        username = parameters['username'] if 'username' in parameters and parameters['username'] else None

    if endpoint_deployment_job_id:
        scan_rows = ddb_service.query_items(sagemaker_endpoint_table,
                                            key_values={'EndpointDeploymentJobId': endpoint_deployment_job_id},
                                            )
    else:
        scan_rows = ddb_service.scan(sagemaker_endpoint_table, filters=None)

    results = []
    user_roles = []

    try:
        if username:
            user_roles = get_user_roles(ddb_service=ddb_service, user_table_name=user_table, username=username)

        if 'username' not in event['headers']:
            return unauthorized()
        requestor_name = event['headers']['username']

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
            if 'status' in row and row['status']['S'] == 'deleted':
                row['endpoint_status']['S'] = EndpointStatus.DELETED.value

            endpoint = EndpointDeploymentJob(**(ddb_service.deserialize(row)))
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

        data = {
            'endpoints': results
        }

        return ok(data=data, decimal=True)
    except Exception as e:
        return bad_request(message=str(e))
