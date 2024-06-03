import json
import logging
import os

import boto3
from aws_lambda_powertools import Tracer

from common.response import ok, not_found
from libs.utils import response_error, log_json

tracer = Tracer()

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

dynamodb = boto3.resource('dynamodb')
workflows_table = dynamodb.Table(os.environ.get('WORKFLOWS_TABLE'))


@tracer.capture_lambda_handler
def handler(event, ctx):
    try:
        logger.info(json.dumps(event))

        name = event['pathParameters']['name']

        inference = workflows_table.get_item(Key={'name': name})

        if 'Item' not in inference:
            return not_found(message=f'workflow with name {name} not found')

        item = inference['Item']

        log_json("inference job", item)

        return ok(data=item, decimal=True)

    except Exception as e:
        return response_error(e)
