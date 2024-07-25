import json
import logging
import os
from dataclasses import dataclass

import boto3
from aws_lambda_powertools import Tracer

from common.excepts import BadRequestException
from common.response import ok, not_found
from libs.utils import response_error, log_json, update_table_by_pk

tracer = Tracer()

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('WORKFLOW_SCHEMA_TABLE')
schemas_table = dynamodb.Table(table_name)


@dataclass
class UpdateSchemaEvent:
    payload: str
    workflow: str = ""


@tracer.capture_lambda_handler
def handler(raw_event, ctx):
    try:
        logger.info(json.dumps(raw_event))
        event = UpdateSchemaEvent(**json.loads(raw_event['body']))

        name = raw_event['pathParameters']['name']

        inference = schemas_table.get_item(Key={'name': name})

        if 'Item' not in inference:
            return not_found(message=f'schema with name {name} not found')

        item = inference['Item']

        log_json("schema", item)

        if not event.workflow and not event.payload:
            raise BadRequestException("At least one of workflow or payload must be provided")

        update_table_by_pk(table=table_name, pk_name='name', pk_value=name, key='workflow', value=event.workflow)
        update_table_by_pk(table=table_name, pk_name='name', pk_value=name, key='payload', value=event.payload)

        return ok(data=item, decimal=True)

    except Exception as e:
        return response_error(e)
