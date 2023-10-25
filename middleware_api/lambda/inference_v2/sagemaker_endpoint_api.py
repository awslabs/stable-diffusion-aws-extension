import os

from common.ddb_service.client import DynamoDbUtilsService
from _types import EndpointDeploymentJob
from multi_users.utils import get_user_roles, check_user_permissions
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from boto3.dynamodb.conditions import Attr, Key
from aws_lambda_powertools import Logger
from _enums import EndpointStatus

import json

logger = Logger(service="sagemaker_endpoint_api", level="INFO")
sagemaker_endpoint_table = os.environ.get('DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME')
user_table = os.environ.get('MULTI_USER_TABLE')

ddb_service = DynamoDbUtilsService(logger=logger)

sagemaker = boto3.client('sagemaker')
ddb_client = boto3.resource('dynamodb')
endpoint_deployment_table = ddb_client.Table(sagemaker_endpoint_table)


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
                                            key_values={'EndpointDeploymentJobId': endpoint_deployment_job_id})
    else:
        scan_rows = ddb_service.scan(sagemaker_endpoint_table, filters=None)

    results = []
    user_roles = []
    if username:
        user_roles = get_user_roles(ddb_service=ddb_service, user_table_name=user_table, username=username)

    if 'x-auth' in event and not event['x-auth']['role']:
        event['x-auth']['role'] = user_roles

    for row in scan_rows:

        # Compatible with fields used in older data, must be 'deleted'
        if 'status' in row and row['status']['S'] == 'deleted':
            row['endpoint_status']['S'] = EndpointStatus.DELETED.value

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


# DELETE /endpoints
def delete_sagemaker_endpoints(event, ctx):
    try:
        # delete sagemaker endpoints in the same loop
        for endpoint in event['delete_endpoint_list']:

            try:
                response = sagemaker.describe_endpoint(EndpointName=endpoint)
                if response['EndpointStatus'] == EndpointStatus.CREATING.value:
                    logger.info('Endpoint in Creating status can not be deleted')
                    return "Endpoint in Creating status can not be deleted"

                logger.info(response)
                delete_response = sagemaker.delete_endpoint(EndpointName=endpoint)
                logger.info(delete_response)

            except (BotoCoreError, ClientError) as error:
                if error.response['Error']['Code'] == 'ResourceNotFound':
                    logger.info("Endpoint not found, no need to delete.")
                else:
                    logger.error(error)

        return "Endpoint deleted"
    except Exception as e:
        logger.error(f"error deleting sagemaker endpoint with exception: {e}")
        return f"error deleting sagemaker endpoint with exception: {e}"
