import json
import logging
import os
from dataclasses import dataclass

import boto3

from common.const import PERMISSION_TRAIN_ALL
from common.response import no_content
from libs.utils import response_error, permissions_check

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

dynamodb = boto3.resource('dynamodb')
training_job_table = dynamodb.Table(os.environ.get('TRAINING_JOB_TABLE'))

s3_bucket_name = os.environ.get('S3_BUCKET_NAME')
s3 = boto3.resource('s3')
bucket = s3.Bucket(s3_bucket_name)


@dataclass
class DeleteTrainingJobsEvent:
    training_id_list: [str]


def handler(event, ctx):
    try:
        logger.info(json.dumps(event))
        body = DeleteTrainingJobsEvent(**json.loads(event['body']))

        permissions_check(event, [PERMISSION_TRAIN_ALL])

        # unique list for preventing duplicate delete
        training_id_list = list(set(body.training_id_list))

        for training_id in training_id_list:

            training = training_job_table.get_item(Key={'id': training_id})

            if 'Item' not in training:
                continue

            logger.info(f'training: {training}')

            training = training['Item']

            if 'input_s3_location' in training:
                prefix = training['input_s3_location'].replace(f"s3://{s3_bucket_name}/", "")
                logger.info(f'delete prefix: {prefix}')
                response = bucket.objects.filter(Prefix=prefix).delete()
                logger.info(f'delete response: {response}')

            if 'params' in training:
                if 'training_params' in training['params']:
                    if 's3_model_path' in training['params']['training_params']:
                        s3_model_path = training['params']['training_params']['s3_model_path']
                        prefix = s3_model_path.replace(f"s3://{s3_bucket_name}/", "")
                        logger.info(f'delete prefix: {prefix}')
                        response = bucket.objects.filter(Prefix=prefix).delete()
                        logger.info(f'delete response: {response}')

            training_job_table.delete_item(Key={'id': training_id})

        return no_content(message='training jobs deleted')
    except Exception as e:
        return response_error(e)
