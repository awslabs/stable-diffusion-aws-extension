import os
import boto3

from aws_lambda_powertools import Logger
from _enums import EndpointStatus

logger = Logger(service="sagemaker_endpoint_event", level="INFO")
sagemaker_endpoint_table = os.environ.get('DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME')
user_table = os.environ.get('MULTI_USER_TABLE')
from common.ddb_service.client import DynamoDbUtilsService

ddb_service = DynamoDbUtilsService(logger=logger)
sagemaker = boto3.client('sagemaker')


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
    ddb_service.update_item(
        table=sagemaker_endpoint_table,
        key={'EndpointDeploymentJobId': endpoint_deployment_job_id['S']},
        field_name='endpoint_status',
        value=get_business_status(endpoint_status)
    )


def get_endpoint_with_endpoint_name(endpoint_name):
    try:
        record_list = ddb_service.scan(table=sagemaker_endpoint_table, filters={
            'endpoint_name': endpoint_name,
        })
        logger.info(record_list)
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
        "DELETING": EndpointStatus.DELETING.value,
    }
    return switcher.get(status, status)
