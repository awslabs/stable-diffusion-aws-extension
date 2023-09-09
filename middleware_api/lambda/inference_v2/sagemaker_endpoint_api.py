import json
import logging
import os

from common.ddb_service.client import DynamoDbUtilsService
from inference_v2._types import EndpointDeploymentJob

sagemaker_endpoint_table = os.environ.get('DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME')


logger = logging.getLogger(__name__)
ddb_service = DynamoDbUtilsService(logger=logger)


# GET /endpoints?last_evaluated_key=xxx&limit=10&name=SageMaker_Endpoint_Name&filter=key:value,key:value
def list_all_sagemaker_endpoints(event, ctx):
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

    if last_evaluated_key and isinstance(last_evaluated_key, str):
        last_evaluated_key = json.loads(last_evaluated_key)

    endpoint_deployment_job_id = parameters['endpointDeploymentJobId'] if 'endpointDeploymentJobId' in parameters and \
                                                                          parameters['endpointDeploymentJobId'] else 0

    last_token = None
    if not endpoint_deployment_job_id:
        result = ddb_service.query_items(sagemaker_endpoint_table,
                                         key_values={'EndpointDeploymentJobId': endpoint_deployment_job_id},
                                         last_evaluated_key=last_evaluated_key,
                                         limit=limit)

        scan_rows = result
        if type(result) is tuple:
            scan_rows = result[0]
            last_token = result[1]
    else:
        scan_rows = ddb_service.scan(sagemaker_endpoint_table, filters=None,
                                     last_evaluated_key=last_evaluated_key,
                                     limit=limit)

    return {
        'statusCode': 200,
        'endpoints': [EndpointDeploymentJob(**(ddb_service.deserialize(endpoint))) for endpoint in scan_rows],
        'last_evaluated_key': last_token
    }
