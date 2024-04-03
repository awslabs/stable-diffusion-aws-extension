import json
import logging
import os

import boto3
from aws_lambda_powertools import Tracer

from common.response import ok, not_found
from libs.utils import response_error, log_json

tracer = Tracer()

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

dynamodb = boto3.resource('dynamodb')
inference_job_table = dynamodb.Table(os.environ.get('INFERENCE_JOB_TABLE'))

s3_bucket_name = os.environ.get('S3_BUCKET_NAME')
s3 = boto3.client('s3')


@tracer.capture_lambda_handler
def handler(event, ctx):
    try:
        logger.info(json.dumps(event))

        inference_id = event['pathParameters']['id']

        return get_infer_data(inference_id)
    except Exception as e:
        return response_error(e)


@tracer.capture_method
def get_infer_data(inference_id: str):
    inference = inference_job_table.get_item(Key={'InferenceJobId': inference_id})

    if 'Item' not in inference:
        return not_found(message=f'inference with id {inference_id} not found')

    item = inference['Item']

    log_json("inference job", item)

    img_presigned_urls = []
    if 'image_names' in item:
        for image_name in item['image_names']:
            presigned_url = generate_presigned_url(s3_bucket_name, f"out/{inference_id}/result/{image_name}")
            img_presigned_urls.append(presigned_url)
    else:
        item['image_names'] = []

    if 'completeTime' not in item:
        item['completeTime'] = None

    output_presigned_urls = generate_presigned_url(
        s3_bucket_name,
        f"out/{inference_id}/result/{inference_id}_param.json")

    data = {
        "img_presigned_urls": img_presigned_urls,
        "output_presigned_urls": [output_presigned_urls],
        **item,
    }

    return ok(data=data, decimal=True)


def generate_presigned_url(bucket_name: str, key: str, expiration=3600) -> str:
    try:
        response = s3.generate_presigned_url('get_object',
                                             Params={'Bucket': bucket_name, 'Key': key},
                                             ExpiresIn=expiration
                                             )
    except Exception as e:
        logger.error(f"Error generating presigned URL: {e}")
        raise

    return response
