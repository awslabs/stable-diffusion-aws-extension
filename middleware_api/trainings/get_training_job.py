import json
import logging
import os

import boto3
from aws_lambda_powertools import Tracer

from common.const import PERMISSION_TRAIN_ALL
from common.response import ok, not_found
from libs.utils import response_error, permissions_check

tracer = Tracer()
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)
bucket_name = os.environ.get("S3_BUCKET_NAME")
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('TRAINING_JOB_TABLE'))
s3 = boto3.client('s3')


@tracer.capture_lambda_handler
def handler(event, ctx):
    try:
        logger.info(json.dumps(event))
        job_id = event['pathParameters']['id']

        permissions_check(event, [PERMISSION_TRAIN_ALL])

        job = table.get_item(Key={'id': job_id})

        if 'Item' not in job:
            return not_found(message=f'Job with id {job_id} not found')

        item = job['Item']

        logger.info(item)

        data = {
            'id': item['id'],
            'job_status': item['job_status'],
            'model_id': item['model_id'],
            'params': item['params'],
            'timestamp': str(item['timestamp']),
            'train_type': item['train_type'],
            'sagemaker_train_name': item['sagemaker_train_name'],
            'logs': item['logs'],
            # todo will remove
            'checkpoint_id': '',
        }

        return ok(data=data, decimal=True)
    except Exception as e:
        return response_error(e)
