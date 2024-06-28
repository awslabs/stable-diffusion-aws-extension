import json
import logging
import os
from dataclasses import dataclass

import boto3
from aws_lambda_powertools import Tracer

from common.ddb_service.client import DynamoDbUtilsService
from common.excepts import BadRequestException
from common.response import no_content
from endpoints.delete_endpoints import get_endpoint_in_sagemaker
from libs.utils import response_error

tracer = Tracer()
table_name = os.environ.get('WORKFLOW_SCHEMA_TABLE')
handler_name = os.environ.get('HANDLER_NAME')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)

s3_resource = boto3.resource('s3')
bucket_name = os.environ.get('S3_BUCKET_NAME')
s3_bucket = s3_resource.Bucket(bucket_name)
lambda_client = boto3.client('lambda')


@dataclass
class DeleteSchemasEvent:
    schema_name_list: [str]


def endpoint_in_use(endpoint_name):
    if get_endpoint_in_sagemaker(endpoint_name):
        raise BadRequestException(f"Endpoint {endpoint_name} is still in use")


@tracer.capture_lambda_handler
def handler(raw_event, ctx):
    try:
        logger.info(json.dumps(raw_event))

        event = DeleteSchemasEvent(**json.loads(raw_event['body']))

        for name in event.schema_name_list:
            ddb_service.delete_item(table=table_name, keys={'name': name})

        return no_content(message="Schemas deleted successfully")
    except Exception as e:
        return response_error(e)
