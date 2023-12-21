import logging
import os

import boto3

from common.response import ok, not_found

logger = logging.getLogger('get_training_job')
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('TRAINING_JOB_TABLE'))

s3 = boto3.resource('s3')
bucket = s3.Bucket(os.environ.get('S3_BUCKET_NAME'))


def handler(event, ctx):
    logger.info(f'event: {event}')
    logger.info(f'ctx: {ctx}')

    job_id = event['pathParameters']['id']

    job = table.get_item(Key={'id': job_id})

    if 'Item' not in job:
        return not_found(message=f'Job with id {job_id} not found')

    item = job['Item']

    data = {
        'id': item['id'],
        'checkpoint_id': item['checkpoint_id'],
        'job_status': item['job_status'],
        'model_id': item['model_id'],
        'params': item['params'],
        'timestamp': item['timestamp'],
        'train_type': item['train_type'],
    }

    return ok(data=data)
