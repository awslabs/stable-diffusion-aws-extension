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
from libs.utils import response_error, update_table_by_pk

tracer = Tracer()
table_name = os.environ.get('WORKFLOWS_TABLE')
ddb_client = boto3.resource('dynamodb')
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)
esd_version = os.environ.get("ESD_VERSION")
s3_resource = boto3.resource('s3')
bucket_name = os.environ.get('S3_BUCKET_NAME')
s3_bucket = s3_resource.Bucket(bucket_name)


@dataclass
class DeleteWorkflowsEvent:
    workflow_name_list: [str]


def endpoint_in_use(endpoint_name):
    if get_endpoint_in_sagemaker(endpoint_name):
        raise BadRequestException(f"Endpoint {endpoint_name} is still in use")


@tracer.capture_lambda_handler
def handler(raw_event, ctx):
    try:
        logger.info(json.dumps(raw_event))

        event = DeleteWorkflowsEvent(**json.loads(raw_event['body']))

        for name in event.workflow_name_list:
            endpoint_in_use(f'comfy-async-{name}')
            endpoint_in_use(f'comfy-real-time-{name}')
            update_table_by_pk(table=table_name, pk_name='name', pk_value=name, key='status', value='Deleting')
            s3_bucket.objects.filter(Prefix=f"comfy/workflows/{name}/").delete()
            ddb_service.delete_item(table=table_name, keys={'name': name})

        return no_content(message="Workflows Deleted")
    except Exception as e:
        return response_error(e)
