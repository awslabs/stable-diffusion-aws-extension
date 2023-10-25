import logging
import os

from common.ddb_service.client import DynamoDbUtilsService
from _types import EndpointDeploymentJob
from multi_users.utils import get_user_roles, check_user_permissions

sagemaker_endpoint_table = os.environ.get('DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME')
user_table = os.environ.get('MULTI_USER_TABLE')

logger = logging.getLogger(__name__)
ddb_service = DynamoDbUtilsService(logger=logger)


# GET /endpoints?name=SageMaker_Endpoint_Name&username=&filter=key:value,key:value
def list_all_sagemaker_endpoints(event, ctx):
    _filter = {}
    if 'queryStringParameters' not in event:
        return {
            'statusCode': '500',
            'error': 'query parameter status and types are needed'
        }

    parameters = event['queryStringParameters']

    endpoint_deployment_job_id = parameters['endpointDeploymentJobId'] if 'endpointDeploymentJobId' in parameters and \
                                                                          parameters[
                                                                              'endpointDeploymentJobId'] else None
    username = parameters['username'] if 'username' in parameters and parameters['username'] else None

    if endpoint_deployment_job_id:
        scan_rows = ddb_service.query_items(sagemaker_endpoint_table,
                                            key_values={'EndpointDeploymentJobId': endpoint_deployment_job_id},
                                            )
    else:
        scan_rows = ddb_service.scan(sagemaker_endpoint_table, )

    results = []
    user_roles = []
    if username:
        user_roles = get_user_roles(ddb_service=ddb_service, user_table_name=user_table, username=username)

    if 'x-auth' in event and not event['x-auth']['role']:
        event['x-auth']['role'] = user_roles

    for row in scan_rows:
        endpoint = EndpointDeploymentJob(**(ddb_service.deserialize(row)))
        if username and check_user_permissions(endpoint.owner_group_or_role, user_roles, username):
            results.append(endpoint.__dict__)
        elif 'x-auth' in event and 'IT Operator' in event['x-auth']['role']:
            # todo: this is not save to do without checking current user roles
            results.append(endpoint.__dict__)

    return {
        'statusCode': 200,
        'endpoints': results
    }

# DELETE /endpoint/{inference_id}
