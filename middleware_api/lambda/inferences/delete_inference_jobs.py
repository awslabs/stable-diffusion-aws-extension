import json
import logging
import os
from dataclasses import dataclass

import boto3

from common.response import no_content

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
inference_job_table = dynamodb.Table(os.environ.get('INFERENCE_JOB_TABLE'))

s3_bucket_name = os.environ.get('S3_BUCKET_NAME')
s3_client = boto3.client('s3')


@dataclass
class DeleteInferenceJobsEvent:
    inference_id_list: [str]


def handler(event, ctx):
    logger.info(f'event: {event}')
    logger.info(f'ctx: {ctx}')

    body = DeleteInferenceJobsEvent(**json.loads(event['body']))

    # unique list for preventing duplicate delete
    inference_id_list = list(set(body.inference_id_list))

    for inference_id in inference_id_list:

        # todo will rename primary key
        inference = inference_job_table.get_item(Key={'InferenceJobId': inference_id})

        if 'Item' not in inference:
            continue

        logger.info(f'inference: {inference}')

        if 'params' not in inference['Item']:
            continue

        params = inference['Item']['params']

        if 'input_body_s3' in params:
            s3_client.delete_object(
                Bucket=s3_bucket_name,
                Key=params['input_body_s3'].replace(f"s3://{s3_bucket_name}/", "")
            )

        if 'output_path' in params:
            s3_client.delete_object(
                Bucket=s3_bucket_name,
                Key=params['output_path'].replace(f"s3://{s3_bucket_name}/", "")
            )

        # todo will rename primary key
        inference_job_table.delete_item(Key={'InferenceJobId': inference_id})

    return no_content(message='inferences deleted')
