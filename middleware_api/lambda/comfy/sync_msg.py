import json
import logging
import os

import boto3

from response import ok

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

msg_table_name = os.environ.get("MSG_TABLE")
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


def handler(raw_event, ctx):
    logger.info("sync msg start...")
    logger.info(f"Received event: {raw_event}")
    if 'Records' not in raw_event or not raw_event['Records']:
        logger.error("ignore empty records msg")
        return ok()
    msg_save = {}
    for message in raw_event['Records']:
        if not message or 'body' not in message:
            logger.error("ignore empty body msg")
            return ok()
        msg = json.loads(message['body'])
        logger.info(f"msg body: {msg}")
        if 'prompt_id' in msg and msg['prompt_id']:
            if msg['prompt_id'] in msg_save.keys():
                msg_save[msg['prompt_id']].append(msg)
            else:
                msg_save[msg['prompt_id']] = []
                msg_save[msg['prompt_id']].append(msg)
    for item in msg_save.keys():
        save_message_to_dynamodb(item, msg_save[item])
    logger.info("execute end...")
    return ok()
