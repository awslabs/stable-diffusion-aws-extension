import json
import logging
import os
from dataclasses import dataclass

import boto3
from aws_lambda_powertools import Tracer

from common.ddb_service.client import DynamoDbUtilsService
from common.response import no_content
from libs.utils import response_error

tracer = Tracer()
table_name = os.environ.get('WORKFLOWS_TABLE')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)

s3_resource = boto3.resource('s3')
bucket_name = os.environ.get('S3_BUCKET_NAME')
s3_bucket = s3_resource.Bucket(bucket_name)


@dataclass
class DeleteWorkflowHandlerEvent:
    name: str


@tracer.capture_lambda_handler
def handler(raw_event, ctx):
    try:
        logger.info(json.dumps(raw_event))

        event = DeleteWorkflowHandlerEvent(**raw_event)

        s3_bucket.objects.filter(Prefix=f"comfy/workflows/{event.name}/").delete()
        ddb_service.delete_item(table=table_name, keys={'name': event.name})

        return no_content(message="Workflows Deleted")
    except Exception as e:
        return response_error(e)
