import json
import logging
import os

import boto3

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok
from common.util import publish_msg
from libs.data_types import TrainJob

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')

train_table = dynamodb.Table(os.environ.get('TRAINING_JOB_TABLE'))
checkpoint_table = dynamodb.Table(os.environ.get('CHECKPOINT_TABLE'))
user_topic_arn = os.environ.get('USER_EMAIL_TOPIC_ARN')

sagemaker = boto3.client('sagemaker')
s3 = boto3.client('s3')

ddb_service = DynamoDbUtilsService(logger=logger)

def handler(event, ctx):
    logger.info(json.dumps(event))

    return ok()

def notify_user(event):
    train_job_id = event['train_job_id']

    raw_train_job = ddb_service.get_item(table=train_table, key_values={
        'id': train_job_id,
    })

    if raw_train_job is None or len(raw_train_job) == 0:
        return {
            'statusCode': 500,
            'msg': f'no such training job find in ddb id[{train_job_id}]'
        }

    train_job = TrainJob(**raw_train_job)

    publish_msg(
        topic_arn=user_topic_arn,
        subject=f'Create Model Job {train_job.sagemaker_train_name} {train_job.job_status}',
        msg=f'to be done with resp: \n {train_job.job_status}'
    )  # todo: find out msg

    return 'job completed'
