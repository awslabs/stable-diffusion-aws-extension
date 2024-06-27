import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime

import boto3
from aws_lambda_powertools import Tracer

from common.ddb_service.client import DynamoDbUtilsService
from common.excepts import BadRequestException
from common.response import ok
from libs.data_types import WorkflowSchema
from libs.utils import response_error

tracer = Tracer()
schemas_table = os.environ.get('WORKFLOW_SCHEMA_TABLE')

aws_region = os.environ.get('AWS_REGION')
s3_bucket_name = os.environ.get('S3_BUCKET_NAME')

esd_version = os.environ.get("ESD_VERSION")
esd_commit_id = os.environ.get("ESD_COMMIT_ID")
dynamodb = boto3.client('dynamodb')
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)


@dataclass
class CreateSchemaEvent:
    name: str
    workflow: str
    payload: str


@tracer.capture_lambda_handler
def handler(raw_event, ctx):
    try:
        logger.info(json.dumps(raw_event))
        event = CreateSchemaEvent(**json.loads(raw_event['body']))

        response = dynamodb.get_item(
            TableName=schemas_table,
            Key={
                'name': {'S': event.name}
            }
        )
        if response.get('Item', None) is not None:
            raise BadRequestException(f"{event.name} already exists")

        data = WorkflowSchema(
            name=event.name,
            payload=event.payload,
            workflow=event.workflow,
            create_time=datetime.utcnow().isoformat(),
        ).__dict__

        ddb_service.put_items(table=schemas_table, entries=data)
        logger.info(f"created schema: {data}")

        return ok(
            message=f"{event.name} created",
            data=data
        )
    except Exception as e:
        return response_error(e)
