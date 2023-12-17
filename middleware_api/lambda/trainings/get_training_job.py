import logging
import os

import boto3

from common.response import ok, not_found

logger = logging.getLogger('get_training_job')
logger.setLevel(logging.INFO)

training_job_table = os.environ.get('TRAINING_JOB_TABLE')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(training_job_table)

s3_bucket_name = os.environ.get('S3_BUCKET_NAME')
s3 = boto3.resource('s3')
bucket = s3.Bucket(s3_bucket_name)


def handler(event, ctx):
    logger.info(f'event: {event}')
    logger.info(f'ctx: {ctx}')

    job_id = event['pathParameters']['id']

    job = table.get_item(Key={'id': job_id})

    if 'Item' not in job:
        return not_found(message=f'Job with id {job_id} not found')

    return ok(data=job['Item'])
