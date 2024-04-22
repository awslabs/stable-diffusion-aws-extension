import json
import logging
import os
import uuid
from decimal import Decimal

import boto3
from aws_lambda_powertools import Tracer

from common.response import ok
from libs.utils import response_error

from common.ddb_service.client import DynamoDbUtilsService
from libs.comfy_data_types import ComfyExecuteTable

from execute import async_inference


tracer = Tracer()
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)


sqs = boto3.client('sqs')
sqs_url = os.environ.get('MERGE_SQS_URL')
execute_table = os.environ.get('EXECUTE_TABLE')
# ddb_service = DynamoDbUtilsService(logger=logger)


def batch_put_items(table_name, items):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)


def convert_float_to_decimal(data):
    if isinstance(data, float):
        return Decimal(str(data))
    elif isinstance(data, dict):
        return {key: convert_float_to_decimal(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_float_to_decimal(item) for item in data]
    else:
        return data


@tracer.capture_lambda_handler
def handler(raw_event, ctx):
    logger.info(f"receive execute reqs start... Received event: {raw_event}")
    try:
        if 'Records' not in raw_event or not raw_event['Records']:
            logger.error("ignore empty records msg")
            return ok()

        execute_merge_req = {}
        execute_merge_req_batch_id = {}
        batch_save_items = []

        for message in raw_event['Records']:
            if not message or 'body' not in message:
                logger.error("ignore empty msg")
                return ok()
            if not "body" in message or not message['body']:
                logger.error("ignore empty body msg")
                return ok()
            merge_job = json.loads(message['body'])
            logger.info(F'merge job: {merge_job}')
            inference_job = merge_job["save_item"]
            event = merge_job["event"]
            inference_id = merge_job["inference_id"]
            batch_save_items.append(inference_job)
            endpoint_name = inference_job["endpoint_name"]

            if (endpoint_name in execute_merge_req and execute_merge_req.get(endpoint_name)
                    and len(execute_merge_req.get(endpoint_name)) > 0):
                execute_merge_req.get(endpoint_name).append(event)
            else:
                batch_id = str(uuid.uuid4())
                execute_merge_req[endpoint_name] = [event]
                execute_merge_req_batch_id[endpoint_name] = batch_id
            inference_job["batch_id"] = execute_merge_req_batch_id.get(endpoint_name)

        for key, vals in execute_merge_req.items():
            resp = async_inference(execute_merge_req.get(key), execute_merge_req_batch_id.get(key), key)
            # TODO status check and save
            logger.info(f"batch async inference response: {resp}")

        batch_put_items(execute_table, convert_float_to_decimal(batch_save_items))
        logger.info("receive execute reqs end...")
        return ok()
    except Exception as e:
        return response_error(e)