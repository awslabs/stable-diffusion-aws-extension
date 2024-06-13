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


def save_message_to_dynamodb(prompt_id, message):
    try:
        response = ddb.get_item(
            TableName=msg_table_name,
            Key={
                'prompt_id': {'S': prompt_id}
            }
        )
        existing_item = response.get('Item')
        if existing_item:
            existing_messages = json.loads(existing_item['message_body']['S'])
            existing_messages.append(message)
            ddb.update_item(
                TableName=msg_table_name,
                Key={
                    'prompt_id': {'S': prompt_id}
                },
                UpdateExpression='SET message_body = :new_messages',
                ExpressionAttributeValues={
                    ':new_messages': {'S': json.dumps(existing_messages)}
                }
            )
            logger.info(f"Message appended to existing record for prompt_id: {prompt_id}")
        else:
            ddb.put_item(
                TableName=msg_table_name,
                Item={
                    'prompt_id': {'S': prompt_id},
                    'message_body': {'S': json.dumps([message])}
                }
            )
            logger.info(f"New record created for prompt_id: {prompt_id}")
    except Exception as e:
        logger.error(f"Error saving message to DynamoDB: {e}")


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
