import json
import logging
import os
from dataclasses import dataclass

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from common.ddb_service.client import DynamoDbUtilsService
from common.response import forbidden, no_content, internal_server_error
from libs.utils import get_permissions_by_username

sagemaker_endpoint_table = os.environ.get('DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME')
user_table = os.environ.get('MULTI_USER_TABLE')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
sagemaker = boto3.client('sagemaker')
ddb_service = DynamoDbUtilsService(logger=logger)


@dataclass
class DeleteEndpointEvent:
    endpoint_name_list: [str]
    username: str


# DELETE /endpoints
def handler(raw_event, ctx):
    try:
        # delete sagemaker endpoints in the same loop
        event = DeleteEndpointEvent(**json.loads(raw_event['body']))

        creator_permissions = get_permissions_by_username(ddb_service, user_table, event.username)
        if 'sagemaker_endpoint' not in creator_permissions or \
                ('all' not in creator_permissions['sagemaker_endpoint'] and 'create' not in creator_permissions[
                    'sagemaker_endpoint']):
            return forbidden(message=f"User {event.username} has no permission to delete a Sagemaker endpoint")

        for endpoint_name in event.endpoint_name_list:
            endpoint_item = get_endpoint_with_endpoint_name(endpoint_name)
            if endpoint_item:
                logger.info("endpoint_name")
                logger.info(json.dumps(endpoint_item))
                # delete sagemaker endpoint
                try:
                    endpoint = sagemaker.describe_endpoint(EndpointName=endpoint_name)
                    if endpoint:
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
                except (BotoCoreError, ClientError) as error:
                    logger.error(error)
                # delete ddb item
                ddb_service.delete_item(
                    table=sagemaker_endpoint_table,
                    keys={'EndpointDeploymentJobId': endpoint_item['EndpointDeploymentJobId']['S']},
                )

        return no_content(message="Endpoints Deleted")
    except Exception as e:
        logger.error(f"error deleting sagemaker endpoint with exception: {e}")
        return internal_server_error(message=f"error deleting sagemaker endpoint with exception: {e}")


def get_endpoint_with_endpoint_name(endpoint_name):
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
