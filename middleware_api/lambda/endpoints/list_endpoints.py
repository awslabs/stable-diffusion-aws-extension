import logging
import os

from common.ddb_service.client import DynamoDbUtilsService
from common.schemas.endpoints import EndpointCollection, EndpointItem, EndpointLink
from common.util import generate_url
from libs.enums import EndpointStatus
from common.response import ok, bad_request
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

    endpoint_collection = EndpointCollection(
        items=[],
        links=[
            EndpointLink(href=generate_url(event, f'endpoints'), rel="self", type="GET"),
            EndpointLink(href=generate_url(event, f'endpoints'), rel="create", type="POST"),
            EndpointLink(href=generate_url(event, f'endpoints'), rel="delete", type="DELETE"),
        ]
    )
    user_roles = []

    try:
        if username:
            user_roles = get_user_roles(ddb_service=ddb_service, user_table_name=user_table, username=username)

        requestor_name = event['requestContext']['authorizer']['username']
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

            endpoint_item = EndpointItem(
                id=endpoint.EndpointDeploymentJobId,
                autoscaling=endpoint.autoscaling,
                current_instance_count=endpoint.current_instance_count,
                name=endpoint.endpoint_name,
                status=endpoint.endpoint_status,
                start_time=endpoint.startTime,
                max_instance_number=endpoint.max_instance_number,
                owner_group_or_role=endpoint.owner_group_or_role,
            )

            if 'sagemaker_endpoint' in requestor_permissions and \
                    'list' in requestor_permissions['sagemaker_endpoint'] and \
                    endpoint.owner_group_or_role and \
                    username and check_user_permissions(endpoint.owner_group_or_role, user_roles, username):
                endpoint_collection.items.append(endpoint_item)
            elif 'sagemaker_endpoint' in requestor_permissions and 'all' in requestor_permissions['sagemaker_endpoint']:
                endpoint_collection.items.append(endpoint_item)

        return ok(data=endpoint_collection.dict(), decimal=True)
    except Exception as e:
        logger.error(e)
        return bad_request(message=str(e))
