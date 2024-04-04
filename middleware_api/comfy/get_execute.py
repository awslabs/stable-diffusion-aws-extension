import logging
import os

import boto3
from aws_lambda_powertools import Tracer
from botocore.exceptions import ClientError

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok, not_found
from common.util import generate_presigned_url_for_job
from libs.comfy_data_types import ComfyExecuteTable
from libs.utils import response_error

tracer = Tracer()
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

region = os.environ.get('AWS_REGION')
bucket_name = os.environ.get('S3_BUCKET_NAME')
execute_table = os.environ.get('EXECUTE_TABLE')
ddb_service = DynamoDbUtilsService(logger=logger)


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


@tracer.capture_lambda_handler
def handler(event, ctx):
    try:
        logger.info(f"get execute start... Received event: {event}")
        logger.info(f"Received ctx: {ctx}")
        prompt_id = event['pathParameters']['id']

        item = ddb_service.get_item(table=execute_table, key_values={"prompt_id": prompt_id})

        if not item:
            return not_found(f"execute not found for prompt_id: {prompt_id}")

        job = ComfyExecuteTable(**generate_presigned_url_for_job(item))
        if not job.output_files:
            job.output_files = []

        if not job.temp_files:
            job.temp_files = []

        return ok(data=item, decimal=True)
    except Exception as e:
        return response_error(e)
