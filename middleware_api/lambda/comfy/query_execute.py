import json
import logging
import os

import boto3
from aws_lambda_powertools import Tracer

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok
from common.util import get_query_param
from libs.utils import response_error, decode_last_key, encode_last_key

tracer = Tracer()
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

region = os.environ.get('AWS_REGION')
bucket_name = os.environ.get('S3_BUCKET_NAME')
execute_table = os.environ.get('EXECUTE_TABLE')
ddb_service = DynamoDbUtilsService(logger=logger)

ddb = boto3.resource('dynamodb')
table = ddb.Table(execute_table)


@tracer.capture_lambda_handler
def handler(event, ctx):
    try:
        exclusive_start_key = get_query_param(event, 'exclusive_start_key')
        limit = int(get_query_param(event, 'limit', 10))

        scan_kwargs = {
            'Limit': limit,
            "ScanIndexForward": False
        }

        if exclusive_start_key:
            scan_kwargs['ExclusiveStartKey'] = decode_last_key(exclusive_start_key)

        logger.info(scan_kwargs)

        response = table.query(**scan_kwargs)

        logger.info(json.dumps(response, default=str))

        items = response.get('Items', [])
        last_evaluated_key = encode_last_key(response.get('LastEvaluatedKey'))

        logger.info(f"query execute start... Received event: {event}")
        logger.info(f"Received ctx: {ctx}")

        data = {
            'items': items,
            'last_evaluated_key': last_evaluated_key
        }

        return ok(data=data, decimal=True)
    except Exception as e:
        return response_error(e)
