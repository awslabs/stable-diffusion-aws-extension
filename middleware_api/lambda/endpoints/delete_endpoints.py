import json
import logging
import os
from dataclasses import dataclass

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from common.const import PERMISSION_ENDPOINT_ALL
from common.ddb_service.client import DynamoDbUtilsService
from common.response import no_content
from libs.utils import permissions_check, response_error

sagemaker_endpoint_table = os.environ.get('DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME')
user_table = os.environ.get('MULTI_USER_TABLE')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

sagemaker = boto3.client('sagemaker')
ddb_service = DynamoDbUtilsService(logger=logger)


@dataclass
class DeleteEndpointEvent:
    endpoint_name_list: [str]
    # todo will be removed
    username: str = ""


# DELETE /endpoints
def handler(raw_event, ctx):
    try:
        permissions_check(raw_event, [PERMISSION_ENDPOINT_ALL])

        # delete sagemaker endpoints in the same loop
        event = DeleteEndpointEvent(**json.loads(raw_event['body']))

        for endpoint_name in event.endpoint_name_list:
            endpoint_item = get_endpoint_with_endpoint_name(endpoint_name)
            if endpoint_item:
                delete_endpoint(endpoint_item)

        return no_content(message="Endpoints Deleted")
    except Exception as e:
        return response_error(e)


def delete_endpoint(endpoint_item):
    logger.info("endpoint_name")
    logger.info(json.dumps(endpoint_item))

    endpoint_name = endpoint_item['endpoint_name']['S']

    endpoint = get_endpoint_in_sagemaker(endpoint_name)

    if endpoint is None:
        delete_endpoint_item(endpoint_item)
        return

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

    # delete ddb item
    delete_endpoint_item(endpoint_item)


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


def get_endpoint_with_endpoint_name(endpoint_name: str):
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
