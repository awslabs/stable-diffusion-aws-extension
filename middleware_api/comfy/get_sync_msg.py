import json
import logging
import os

import boto3
from aws_lambda_powertools import Tracer

from common.response import ok, no_content
from libs.utils import response_error

tracer = Tracer()
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

msg_table_name = os.environ.get('MSG_TABLE')
ddb = boto3.client('dynamodb')
sqs_url = os.environ.get('SQS_URL')
sqs = boto3.client('sqs')


def read_messages_from_dynamodb(prompt_id):
    try:
        # process_sqs_messages_and_write_to_ddb(prompt_id)
        response = ddb.query(
            TableName=msg_table_name,
            KeyConditionExpression='prompt_id = :pid',
            ExpressionAttributeValues={':pid': {'S': prompt_id}},
        )
        messages = [json.loads(item['message_body']['S']) for item in response.get('Items', [])]
        logger.info("read_messages_from_dynamodb response: {}".format(messages))
        return messages
    except Exception as e:
        logger.error(f"Error reading messages from DynamoDB: {e}")
        return []


@tracer.capture_lambda_handler
def handler(event, ctx):
    try:
        logger.info(f"get msg start... Received event: {event} ctx: {ctx}")
        if 'pathParameters' not in event or not event['pathParameters'] or not event['pathParameters']['id']:
            return no_content()
        prompt_id = event['pathParameters']['id']
        response = read_messages_from_dynamodb(prompt_id)
        logger.info(f"get msg end... response: {response}")
        return ok(data=response)
    except Exception as e:
        return response_error(e)
