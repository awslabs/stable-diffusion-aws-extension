import json
import logging
import os
from datetime import datetime

import boto3
from aws_lambda_powertools import Tracer

from common.ddb_service.client import DynamoDbUtilsService
from common.util import s3_scan_files, load_json_from_s3
from libs.comfy_data_types import InferenceResult

tracer = Tracer()
s3_resource = boto3.resource('s3')

sns_topic = os.environ['NOTICE_SNS_TOPIC']
bucket_name = os.environ['S3_BUCKET_NAME']
job_table = os.environ['INFERENCE_JOB_TABLE']
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)


@tracer.capture_lambda_handler
def handler(event, context):
    logger.info(json.dumps(event))
    message = event['Records'][0]['Sns']['Message']
    message = json.loads(message)

    logger.info(message)

    if 'invocationStatus' not in message:
        # maybe a message from SNS for test
        logger.error("Not a valid sagemaker inference result message")
        return

    result = load_json_from_s3(message['responseParameters']['outputLocation'])

    logger.info(result)

    result = {
        "prompt_id": '11111111-1111-1111',
        "instance_id": 'esd-real-time-test-rgihbd',
        "status": 'success',
        "output_path": f's3://{bucket_name}/template/',
        "temp_path": f's3://{bucket_name}/template/'
    }

    result = InferenceResult(**result)

    result = s3_scan_files(result)

    if message["invocationStatus"] != "Completed":
        result.status = "failed"

    logger.info(result)

    key = {"prompt_id": result.prompt_id}
    ddb_service.update_item(table=job_table, key=key, field_name="status", value=result.status)
    ddb_service.update_item(table=job_table, key=key, field_name="output_path", value=result.output_path)
    ddb_service.update_item(table=job_table, key=key, field_name="output_files", value=result.output_files)
    ddb_service.update_item(table=job_table, key=key, field_name="temp_path", value=result.temp_path)
    ddb_service.update_item(table=job_table, key=key, field_name="temp_files", value=result.temp_files)
    ddb_service.update_item(table=job_table, key=key, field_name="complete_time",
                            value=datetime.now().isoformat())

    return {}
