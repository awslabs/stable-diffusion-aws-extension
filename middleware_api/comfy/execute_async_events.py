import json
import logging
import os
from datetime import datetime

import boto3
from aws_lambda_powertools import Tracer

from common.ddb_service.client import DynamoDbUtilsService
from common.util import s3_scan_files, load_json_from_s3, record_count_metrics
from libs.comfy_data_types import InferenceResult

tracer = Tracer()
s3_resource = boto3.resource('s3')

sns_topic = os.environ['NOTICE_SNS_TOPIC']
bucket_name = os.environ['S3_BUCKET_NAME']

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)

job_table = os.environ['EXECUTE_TABLE']
ddb_client = boto3.resource('dynamodb')
inference_table = ddb_client.Table(job_table)


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

    results = load_json_from_s3(message['responseParameters']['outputLocation'])

    logger.info(results)

    for item in results:
        result = InferenceResult(**item)

        result = s3_scan_files(result)

        if message["invocationStatus"] != "Completed":
            result.status = "failed"
            record_count_metrics(metric_name='InferenceFailed', service='Comfy')
        else:
            record_count_metrics(metric_name='InferenceSucceed', service='Comfy')

        logger.info(result)

        update_inference_job_table(prompt_id=result.prompt_id, key="status", value=result.status)
        update_inference_job_table(prompt_id=result.prompt_id, key="output_path", value=result.output_path)
        update_inference_job_table(prompt_id=result.prompt_id, key="output_files", value=result.output_files)
        update_inference_job_table(prompt_id=result.prompt_id, key="temp_path", value=result.temp_path)
        update_inference_job_table(prompt_id=result.prompt_id, key="temp_files", value=result.temp_files)
        update_inference_job_table(prompt_id=result.prompt_id, key="complete_time", value=datetime.now().isoformat())

        # todo log time
        resp = inference_table.get_item(Key={"prompt_id": result.prompt_id})
        logger.info(resp)

    return {}


def update_inference_job_table(prompt_id, key, value):
    logger.info(f"Update inference job table with prompt_id: {prompt_id}, key: {key}, value: {value}")

    inference_table.update_item(
        Key={
            "prompt_id": prompt_id,
        },
        UpdateExpression=f"set #k = :r",
        ExpressionAttributeNames={'#k': key},
        ExpressionAttributeValues={':r': value},
        ReturnValues="UPDATED_NEW"
    )
