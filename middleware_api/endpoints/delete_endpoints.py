import json
import logging
import os
from dataclasses import dataclass

import boto3
from aws_lambda_powertools import Tracer
from botocore.exceptions import BotoCoreError, ClientError

from common.ddb_service.client import DynamoDbUtilsService
from common.response import no_content
from endpoint_event import update_endpoint_field
from libs.enums import EndpointStatus
from libs.utils import response_error

tracer = Tracer()
sagemaker_endpoint_table = os.environ.get('ENDPOINT_TABLE_NAME')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

cw_client = boto3.client('cloudwatch')
sagemaker = boto3.client('sagemaker')
ddb_service = DynamoDbUtilsService(logger=logger)
esd_version = os.environ.get("ESD_VERSION")

s3 = boto3.resource('s3')
s3_bucket_name = os.environ.get('S3_BUCKET_NAME')
bucket = s3.Bucket(s3_bucket_name)


@dataclass
class DeleteEndpointEvent:
    endpoint_name_list: [str]
    # todo will be removed
    username: str = ""


# DELETE /endpoints
@tracer.capture_lambda_handler
def handler(raw_event, ctx):
    try:
        logger.info(json.dumps(raw_event))
        # todo will be removed
        # permissions_check(raw_event, [PERMISSION_ENDPOINT_ALL])

        # delete sagemaker endpoints in the same loop
        event = DeleteEndpointEvent(**json.loads(raw_event['body']))

        for endpoint_name in event.endpoint_name_list:
            endpoint_item = get_endpoint_with_endpoint_name(endpoint_name)
            if endpoint_item:
                delete_endpoint(endpoint_item)

        return no_content(message="Endpoints Deleted")
    except Exception as e:
        return response_error(e)


@tracer.capture_method
def delete_endpoint(endpoint_item):
    tracer.put_annotation("endpoint_item", endpoint_item)
    logger.info("endpoint_name")
    logger.info(json.dumps(endpoint_item))

    endpoint_name = endpoint_item['endpoint_name']['S']
    ep_id = endpoint_item['EndpointDeploymentJobId']

    endpoint = get_endpoint_in_sagemaker(endpoint_name)

    if endpoint is None:
        delete_endpoint_item(endpoint_item)
        return

    update_endpoint_field(ep_id, 'endpoint_status', EndpointStatus.DELETED.value)
    update_endpoint_field(ep_id, 'current_instance_count', 0)

    # delete sagemaker endpoint
    logger.info("endpoint")
    logger.info(endpoint)
    sagemaker.delete_endpoint(EndpointName=endpoint_name)
    config = sagemaker.describe_endpoint_config(EndpointConfigName=endpoint['EndpointConfigName'])
    if config:
        logger.info("config")
        logger.info(config)
        sagemaker.delete_endpoint_config(EndpointConfigName=endpoint['EndpointConfigName'])
        for ProductionVariant in config['ProductionVariants']:
            sagemaker.delete_model(ModelName=ProductionVariant['ModelName'])

    response = cw_client.delete_alarms(
        AlarmNames=[f'{endpoint_name}-HasBacklogWithoutCapacity-Alarm'],
    )
    logger.info(f"delete_metric_alarm response: {response}")

    # delete ddb item
    delete_endpoint_item(endpoint_item)


@tracer.capture_method
def get_endpoint_in_sagemaker(endpoint_name):
    try:
        return sagemaker.describe_endpoint(EndpointName=endpoint_name)
    except (BotoCoreError, ClientError) as error:
        logger.error(error)
        return None


def delete_endpoint_item(endpoint_item):
    ddb_service.delete_item(
        table=sagemaker_endpoint_table,
        keys={'EndpointDeploymentJobId': endpoint_item['EndpointDeploymentJobId']['S']},
    )


@tracer.capture_method
def get_endpoint_with_endpoint_name(endpoint_name: str):
    tracer.put_annotation("endpoint_name", endpoint_name)
    try:
        record_list = ddb_service.scan(table=sagemaker_endpoint_table, filters={
            'endpoint_name': endpoint_name,
        })

        if len(record_list) == 0:
            logger.error("There is no endpoint deployment job info item with endpoint name: " + endpoint_name)
            return {}

        logger.info(record_list[0])
        return record_list[0]
    except Exception as e:
        logger.error(e)
        return {}
