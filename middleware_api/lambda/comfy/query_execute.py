import base64
import json
import logging
import os
from dataclasses import dataclass

import boto3
from aws_lambda_powertools import Tracer
from botocore.exceptions import ClientError

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok, not_found
from libs.comfy_data_types import ComfyExecuteTable
from libs.enums import ComfyExecuteRespType
from libs.utils import response_error

tracer = Tracer()
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

region = os.environ.get('AWS_REGION')
bucket_name = os.environ.get('S3_BUCKET_NAME')
execute_table = os.environ.get('EXECUTE_TABLE')
ddb_service = DynamoDbUtilsService(logger=logger)


@dataclass
class QueryExecuteEvent:
    prompt_id: str
    resp_type: ComfyExecuteRespType


def generate_presigned_url(bucket, key, expiration=3600):
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


def get_s3_file_base64(bucket, key):
    s3_client = boto3.client('s3', region_name=region)
    try:
        response = s3_client.get_object(
            Bucket=bucket,
            Key=key
        )
        file_content = response['Body'].read()
        file_base64 = base64.b64encode(file_content).decode('utf-8')
        return file_base64
    except ClientError as e:
        logger.error(f"Error getting file from S3: {e}")
        return None


def build_ddb_execute_response(prompt_id, resp_type):
    result = ddb_service.get_item(table=execute_table, key_values={
        'prompt_id': prompt_id
    })
    if 'Item' not in result:
        return not_found(message=f'execute with id {prompt_id} not found')

    execute_item = ComfyExecuteTable(**result)
    response = execute_item.__dict__
    file_urls = {}
    file_base64 = {}
    if resp_type == ComfyExecuteRespType.PRESIGN_URL:
        if len(execute_item.output_files) < 0:
            return response
        for file_name in execute_item.output_files:
            if not file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.mp4', '.mov', '.avi')):
                continue
            # TODO output_path: f'output/{prompt_id}/{file_name}'
            file_urls[file_name] = generate_presigned_url(bucket_name, f'{execute_item.output_path}/{file_name}')
        response['image_video_data_url'] = file_urls
    elif resp_type == ComfyExecuteRespType.BASE64:
        if len(execute_item.output_files) < 0:
            return response
        for file_name in execute_item.output_files:
            if not file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.mp4', '.mov', '.avi')):
                continue
            file_base64[file_name] = get_s3_file_base64(bucket_name, f'{execute_item.output_path}/{file_name}')
        response['image_video_data_base64'] = file_base64
    return response


@tracer.capture_lambda_handler
def handler(event, ctx):
    try:
        logger.info(f"query execute start... Received event: {event}")
        logger.info(f"Received ctx: {ctx}")
        event = QueryExecuteEvent(**json.loads(event['body']))
        prompt_id = event.prompt_id
        resp_type = event.resp_type
        response = build_ddb_execute_response(prompt_id, resp_type)
        logger.info(f"query execute end... response: {response}")
        return ok(data=response)
    except Exception as e:
        return response_error(e)
