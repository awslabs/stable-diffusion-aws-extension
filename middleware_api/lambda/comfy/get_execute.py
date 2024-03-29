import logging
import os

import boto3
from aws_lambda_powertools import Tracer
from botocore.exceptions import ClientError

from common.response import ok
from libs.utils import response_error

tracer = Tracer()
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

region = os.environ.get('AWS_REGION')
bucket_name = os.environ.get('S3_BUCKET_NAME')


def generate_presigned_url(bucket, key, expiration=3600):
    """Generate a presigned URL for the S3 object."""
    s3_client = boto3.client('s3', region_name=region)
    try:
        response = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=expiration
        )
    except ClientError as e:
        logger.error(f"Error generating presigned URL: {e}")
        return None

    return response


def build_s3_images_request(prompt_id, bucket_name, s3_path):
    s3 = boto3.client('s3', region_name=region)
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=s3_path)
    image_video_dict = {}
    for obj in response.get('Contents', []):
        object_key = obj['Key']
        file_name = object_key.split('/')[-1]
        if object_key.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.mp4', '.mov', '.avi')):
            # response_data = s3.get_object(Bucket=bucket_name, Key=object_key)
            # object_data = response_data['Body'].read()
            # encoded_data = base64.b64encode(object_data).decode('utf-8')
            # image_video_dict[file_name] = encoded_data
            presigned_url = generate_presigned_url(bucket_name, object_key)
            image_video_dict[file_name] = presigned_url

    return {'prompt_id': prompt_id, 'image_video_data': image_video_dict}


@tracer.capture_lambda_handler
def handler(event, ctx):
    try:
        logger.info(f"get execute start... Received event: {event}")
        logger.info(f"Received ctx: {ctx}")
        prompt_id = event['pathParameters']['id']
        response = build_s3_images_request(prompt_id, bucket_name, f'output/{prompt_id}')
        logger.info(f"get execute end... response: {response}")
        return ok(data=response)
    except Exception as e:
        return response_error(e)
