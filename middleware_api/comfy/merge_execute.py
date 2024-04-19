import json
import logging
import os
import uuid

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
ddb_service = DynamoDbUtilsService(logger=logger)


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
                logger.error("ignore empty body msg")
                return ok()
            inference_job = ComfyExecuteTable(**json.loads(message['body']))

            batch_save_items.append(inference_job.__dict__)
            endpoint_name = inference_job.endpoint_name

            if endpoint_name in execute_merge_req and execute_merge_req.get(endpoint_name) and len(execute_merge_req.get(endpoint_name)) > 0:
                execute_merge_req.get(endpoint_name).append(inference_job.__dict__)
            else:
                batch_id = uuid.uuid4().hex
                execute_merge_req[endpoint_name] = [inference_job.__dict__]
                execute_merge_req_batch_id[endpoint_name] = batch_id
            inference_job.batch_id = execute_merge_req_batch_id.get(endpoint_name)

        for key, vals in execute_merge_req.items():
            resp = async_inference(execute_merge_req.get(key), execute_merge_req_batch_id.get(key), key)
            # TODO status check and save
            logger.info(f"batch async inference response: {resp}")

        ddb_service.batch_put_items(execute_table, entries={execute_table: batch_save_items})
        logger.info("receive execute reqs end...")
        return ok()
    except Exception as e:
        return response_error(e)