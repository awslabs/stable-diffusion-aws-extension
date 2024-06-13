import json
import logging
import os
import uuid
from decimal import Decimal

import boto3
from aws_lambda_powertools import Tracer

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok
from libs.utils import response_error


from execute import async_inference
from execute import ComfyExecuteTable


tracer = Tracer()
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)


sqs = boto3.client('sqs')
sqs_url = os.environ.get('MERGE_SQS_URL')
execute_table_name = os.environ.get('EXECUTE_TABLE')
ddb_service = DynamoDbUtilsService(logger=logger)
dynamodb = boto3.resource('dynamodb')
execute_table = dynamodb.Table(execute_table_name)


def update_execute_job_table(prompt_id, key, value):
    logger.info(f"Update execute table with prompt_id: {prompt_id}, key: {key}, value: {value}")
    try:
        execute_table.update_item(
            Key={
                "prompt_id": prompt_id,
            },
            UpdateExpression=f"set #k = :r",
            ExpressionAttributeNames={'#k': key},
            ExpressionAttributeValues={':r': value},
            ConditionExpression="attribute_exists(prompt_id)",
            ReturnValues="UPDATED_NEW"
        )
    except Exception as e:
        logger.error(f"Update execute job table error: {e}")
        raise e


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
        # batch_save_items = []

        for message in raw_event['Records']:
            if not message or 'body' not in message:
                logger.error("ignore empty msg")
                return ok()
            if not message['body']:
                logger.error("ignore empty body msg")
                return ok()
            merge_job = json.loads(message['body'])
            logger.info(F'merge job: {merge_job}')
            inference_job = ComfyExecuteTable(**merge_job["save_item"])
            event = merge_job["event"]
            inference_id = merge_job["inference_id"]
            # batch_save_items.append(inference_job)
            endpoint_name = inference_job.endpoint_name

            if (endpoint_name in execute_merge_req and execute_merge_req.get(endpoint_name)
                    and len(execute_merge_req.get(endpoint_name)) > 0):
                execute_merge_req.get(endpoint_name).append(event)
            else:
                batch_id = str(uuid.uuid4())
                execute_merge_req[endpoint_name] = [event]
                execute_merge_req_batch_id[endpoint_name] = batch_id
            inference_job.batch_id = execute_merge_req_batch_id.get(endpoint_name)
            logger.info(F'update inference job batch_id: {inference_job.batch_id}, prompt_id: {inference_job.prompt_id}')
            update_execute_job_table(prompt_id=inference_job.prompt_id, key="batch_id", value=inference_job.batch_id)
            # logger.info(F'save inference job: {inference_job.__dict__}')
            # ddb_service.put_items(execute_table, entries=inference_job.__dict__)

        for key, vals in execute_merge_req.items():
            resp = async_inference(execute_merge_req.get(key), execute_merge_req_batch_id.get(key), key)
            # TODO status check and save
            logger.info(f"batch async inference response: {resp}")
            # resp1 = async_inference(execute_merge_req.get(key), execute_merge_req_batch_id.get(key) + "111", key)
            # logger.info(f"batch async inference multi 11111 test response: {resp1}")
            # resp2 = async_inference(execute_merge_req.get(key), execute_merge_req_batch_id.get(key) + "222", key)
            # logger.info(f"batch async inference multi 22222 test response: {resp2}")
            # resp3 = async_inference(execute_merge_req.get(key), execute_merge_req_batch_id.get(key) + "333", key)
            # logger.info(f"batch async inference multi 3333 test response: {resp3}")
            # resp4 = async_inference(execute_merge_req.get(key), execute_merge_req_batch_id.get(key) + "444", key)
            # logger.info(f"batch async inference multi 4444 test response: {resp4}")


        # batch_put_items(execute_table, convert_float_to_decimal(batch_save_items))
        logger.info("receive execute reqs end...")
        return ok()
    except Exception as e:
        return response_error(e)