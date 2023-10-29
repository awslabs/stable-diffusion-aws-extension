import os
import boto3

from aws_lambda_powertools import Logger
from boto3.dynamodb.conditions import Attr
from _enums import EndpointStatus

logger = Logger(service="sagemaker_endpoint_event", level="INFO")
sagemaker_endpoint_table = os.environ.get('DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME')
user_table = os.environ.get('MULTI_USER_TABLE')

sagemaker = boto3.client('sagemaker')
ddb_client = boto3.resource('dynamodb')
endpoint_deployment_table = ddb_client.Table(sagemaker_endpoint_table)


def event_handler(event, context):
    logger.info(event)
    endpoint_name = event['detail']['EndpointName']
    endpoint_status = event['detail']['EndpointStatus']

    data = get_endpoint_with_endpoint_name(endpoint_name)
    if data:
        endpoint_deployment_job_id = data['EndpointDeploymentJobId']
        update_endpoint_status(endpoint_deployment_job_id, endpoint_status)
    else:
        logger.error(f"No matching DynamoDB record found for endpoint: {endpoint_name}")


def update_endpoint_status(endpoint_deployment_job_id, endpoint_status):
    logger.info(f"Updating DynamoDB status for: {endpoint_deployment_job_id}")
    endpoint_deployment_table.update_item(
        Key={
            'EndpointDeploymentJobId': endpoint_deployment_job_id
        },
        UpdateExpression="SET #s = :s",
        ExpressionAttributeNames={
            '#s': 'endpoint_status'
        },
        ExpressionAttributeValues={
            ':s': get_business_status(endpoint_status)
        }
    )


def get_endpoint_with_endpoint_name(endpoint_name):
    try:
        resp = endpoint_deployment_table.scan(
            FilterExpression=Attr('endpoint_name').eq(endpoint_name)
        )
        logger.info(resp)
        record_list = resp['Items']
        if len(record_list) == 0:
            logger.error("There is no endpoint deployment job info item with endpoint name:" + endpoint_name)
            return {}

        return record_list[0]
    except Exception as e:
        logger.error(e)
        return {}


def get_business_status(status):
    """
    Convert SageMaker endpoint status to business status
    :param status: EventBridge event status(upper case)
    :return: business status
    """
    switcher = {
        "IN_SERVICE": EndpointStatus.IN_SERVICE.value,
        "CREATING": EndpointStatus.CREATING.value,
        "DELETED": EndpointStatus.DELETED.value,
        "FAILED": EndpointStatus.FAILED.value,
        "UPDATING": EndpointStatus.UPDATING.value,
    }
    return switcher.get(status, status)
