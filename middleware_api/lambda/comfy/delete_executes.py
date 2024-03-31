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
job_table = dynamodb.Table(os.environ.get('EXECUTE_TABLE'))

s3_bucket_name = os.environ.get('S3_BUCKET_NAME')
s3_client = boto3.client('s3')


@dataclass
class DeleteEvent:
    execute_id_list: [str]


@tracer.capture_lambda_handler
def handler(event, ctx):
    try:
        logger.info(json.dumps(event))

        body = DeleteEvent(**json.loads(event['body']))

        # todo will be removed
        # permissions_check(event, [PERMISSION_INFERENCE_ALL])

        # unique list for preventing duplicate delete
        execute_id_list = list(set(body.execute_id_list))

        for prompt_id in execute_id_list:

            # todo will rename primary key
            execute = job_table.get_item(Key={'prompt_id': prompt_id})

            if 'Item' not in execute:
                continue

            item = execute['Item']

            logger.info(f'item: {item}')

            # if 'input_body_s3' in params:
            #     s3_client.delete_object(
            #         Bucket=s3_bucket_name,
            #         Key=params['input_body_s3'].replace(f"s3://{s3_bucket_name}/", "")
            #     )
            #
            # if 'output_path' in params:
            #     s3_client.delete_object(
            #         Bucket=s3_bucket_name,
            #         Key=params['output_path'].replace(f"s3://{s3_bucket_name}/", "")
            #     )

            job_table.delete_item(Key={'prompt_id': prompt_id})

        return no_content(message='execute deleted')
    except Exception as e:
        return response_error(e)
