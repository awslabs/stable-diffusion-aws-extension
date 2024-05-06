import json
import logging
import os

import boto3
from aws_lambda_powertools import Tracer
from boto3.dynamodb.conditions import Key

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok
from libs.utils import response_error

tracer = Tracer()
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)
ddb = boto3.resource('dynamodb')

ddb_service = DynamoDbUtilsService(logger=logger)
table = ddb.Table(os.environ.get('LOG_SUB_TABLE'))


@tracer.capture_lambda_handler
def handler(event, ctx):
    try:
        logger.info(f"get execute start... Received event: {event}")
        logger.info(f"Received ctx: {ctx}")
        prompt_id = event['pathParameters']['id']

        scan_kwargs = {
            'Limit': 1000,
            'IndexName': "message_type-timestamp-index",
            'KeyConditionExpression': Key('message_type').eq(prompt_id),
            "ScanIndexForward": False
        }

        logger.info(scan_kwargs)

        response = table.query(**scan_kwargs)

        logger.info(json.dumps(response, default=str))

        items = response.get('Items', [])

        items.sort(key=lambda x: x['id'])

        return ok(data={'logs': items}, decimal=True)
    except Exception as e:
        return response_error(e)
