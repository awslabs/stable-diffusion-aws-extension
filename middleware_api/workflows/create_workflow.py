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
from libs.data_types import Workflow
from libs.utils import response_error, check_file_exists

tracer = Tracer()
workflows_table = os.environ.get('WORKFLOWS_TABLE')

aws_region = os.environ.get('AWS_REGION')
s3_bucket_name = os.environ.get('S3_BUCKET_NAME')

esd_version = os.environ.get("ESD_VERSION")
esd_commit_id = os.environ.get("ESD_COMMIT_ID")
dynamodb = boto3.client('dynamodb')
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)


@dataclass
class CreateWorkflowEvent:
    name: str
    image_uri: str
    payload_json: str


@tracer.capture_lambda_handler
def handler(raw_event, ctx):
    try:
        logger.info(json.dumps(raw_event))
        event = CreateWorkflowEvent(**json.loads(raw_event['body']))

        response = dynamodb.get_item(
            TableName=workflows_table,
            Key={
                'name': {'S': event.name}
            }
        )
        if response.get('Item', None) is not None:
            raise BadRequestException(f"{event.name} already exists")

        s3_location = f"comfy/workflows/{event.name}/"

        if not check_file_exists(f"{s3_location}lock"):
            raise BadRequestException(f"workflow {event.name} files not ready")

        data = Workflow(
            name=event.name,
            s3_location=s3_location,
            image_uri=event.image_uri,
            payload_json=event.payload_json,
            status='Enabled',
            create_time=datetime.utcnow().isoformat(),
        ).__dict__

        ddb_service.put_items(table=workflows_table, entries=data)
        logger.info(f"created workflow: {data}")

        return ok(
            message=f"{event.name} created",
            data=data
        )
    except Exception as e:
        return response_error(e)
