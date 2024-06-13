import json
import logging
import os
from dataclasses import dataclass

import boto3
from aws_lambda_powertools import Tracer

from common.response import no_content
from libs.utils import response_error

tracer = Tracer()
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

dynamodb = boto3.resource('dynamodb')
checkpoints_table = dynamodb.Table(os.environ.get('CHECKPOINTS_TABLE'))

s3_bucket_name = os.environ.get('S3_BUCKET_NAME')
s3 = boto3.resource('s3')
bucket = s3.Bucket(s3_bucket_name)


@dataclass
class DeleteCheckpointsEvent:
    checkpoint_id_list: [str]


@tracer.capture_lambda_handler
def handler(event, ctx):
    try:
        logger.info(json.dumps(event))
        # todo will be removed
        # permissions_check(event, [PERMISSION_CHECKPOINT_ALL])

        body = DeleteCheckpointsEvent(**json.loads(event['body']))

        # unique list for preventing duplicate delete
        checkpoint_id_list = list(set(body.checkpoint_id_list))

        for checkpoint_id in checkpoint_id_list:

            checkpoint = checkpoints_table.get_item(Key={'id': checkpoint_id})

            if 'Item' not in checkpoint:
                continue

            logger.info(f'checkpoint: {checkpoint}')

            checkpoint_names = checkpoint['Item']['checkpoint_names']
            s3_location = checkpoint['Item']['s3_location']
            object_prefix = s3_location.replace(f"s3://{s3_bucket_name}/", "")

            for checkpoint_name in checkpoint_names:
                object_key = f'{object_prefix}/{checkpoint_name}'
                logger.info(f'object_key: {object_key}')
                bucket.Object(object_key).delete()

            checkpoints_table.delete_item(Key={'id': checkpoint_id})

        return no_content(message='checkpoints deleted')
    except Exception as e:
        return response_error(e)
