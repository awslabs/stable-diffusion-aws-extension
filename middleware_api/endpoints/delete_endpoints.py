import json
import logging
import os
from dataclasses import dataclass

import boto3
from aws_lambda_powertools import Tracer
from botocore.exceptions import BotoCoreError, ClientError

from common.ddb_service.client import DynamoDbUtilsService
from common.excepts import NotFoundException
from common.response import no_content
from common.util import endpoint_clean
from libs.data_types import Endpoint
from libs.enums import EndpointStatus
from libs.utils import response_error, get_endpoint_by_name

tracer = Tracer()
sagemaker_endpoint_table = os.environ.get('ENDPOINT_TABLE_NAME')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

sagemaker = boto3.client('sagemaker')
ddb_service = DynamoDbUtilsService(logger=logger)
esd_version = os.environ.get("ESD_VERSION")


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

        event = DeleteEndpointEvent(**json.loads(raw_event['body']))

        for endpoint_name in event.endpoint_name_list:
            try:
                ep = get_endpoint_by_name(endpoint_name)
                delete_endpoint(ep)
            except Exception as e:
                if isinstance(e, NotFoundException):
                    continue
                raise e

        return no_content(message="Endpoints Deleted")
    except Exception as e:
        return response_error(e)


def update_endpoint_field(ep: Endpoint, field_name, field_value):
    logger.info(f"Updating {field_name} to {field_value} for: {ep.EndpointDeploymentJobId}")
    ddb_service.update_item(
        table=sagemaker_endpoint_table,
        key={'EndpointDeploymentJobId': ep.EndpointDeploymentJobId},
        field_name=field_name,
        value=field_value
    )


@tracer.capture_method
def delete_endpoint(ep: Endpoint):
    update_endpoint_field(ep, 'endpoint_status', EndpointStatus.DELETED.value)
    update_endpoint_field(ep, 'current_instance_count', 0)

    endpoint = get_endpoint_in_sagemaker(ep.endpoint_name)
    if endpoint is None:
        endpoint_clean(ep)
        return

    sagemaker.delete_endpoint(EndpointName=ep.endpoint_name)

    endpoint_clean(ep)


@tracer.capture_method
def get_endpoint_in_sagemaker(endpoint_name):
    try:
        return sagemaker.describe_endpoint(EndpointName=endpoint_name)
    except (BotoCoreError, ClientError) as error:
        logger.error(error, exc_info=True)
        return None
