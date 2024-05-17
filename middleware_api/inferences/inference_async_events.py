import json
import logging
import os

import boto3
from aws_lambda_powertools import Tracer

from common.sns_util import send_message_to_sns
from common.util import record_latency_metrics, record_count_metrics
from inference_libs import parse_sagemaker_result, get_bucket_and_key, get_inference_job
from start_inference_job import update_inference_job_table

tracer = Tracer()
s3_resource = boto3.resource('s3')

SNS_TOPIC = os.environ['NOTICE_SNS_TOPIC']

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)


@tracer.capture_lambda_handler
def handler(event, context):
    logger.info(json.dumps(event))

    message = event['Records'][0]['Sns']['Message']
    message = json.loads(message)

    if 'invocationStatus' not in message:
        # maybe a message from SNS for test
        logger.error("Not a valid sagemaker inference result message")
        return

    invocation_status = message["invocationStatus"]
    inference_id = message["inferenceId"]
    job = get_inference_job(inference_id)

    # Get the task type
    task_type = job.get('taskType', 'txt2img')
    workflow = job.get('workflow', None)
    create_time = job.get('createTime')

    endpoint_name = message["requestParameters"]["endpointName"]

    if invocation_status != "Completed":
        update_inference_job_table(inference_id, 'status', 'failed')
        update_inference_job_table(inference_id, 'sagemakerRaw', str(message))
        print(f"Not complete invocation!")
        send_message_to_sns(message, SNS_TOPIC)
        record_count_metrics(ep_name=endpoint_name,
                             metric_name='InferenceFailed',
                             workflow=workflow
                             )
        return message

    output_location = message["responseParameters"]["outputLocation"]
    bucket, key = get_bucket_and_key(output_location)
    obj = s3_resource.Object(bucket, key)
    body = obj.get()['Body'].read().decode('utf-8')

    print(f"Sagemaker Out Body: {body}")

    sagemaker_out = json.loads(body)
    if sagemaker_out is None:
        update_inference_job_table(inference_id, 'status', 'failed')
        message_json = {
            'InferenceJobId': inference_id,
            'status': "failed",
            'reason': "Sagemaker inference invocation completed, but the sagemaker output failed to be parsed as json"
        }
        send_message_to_sns(message_json, SNS_TOPIC)
        raise ValueError("body contains invalid JSON")

    parse_sagemaker_result(sagemaker_out, create_time, inference_id, task_type, endpoint_name)

    record_count_metrics(ep_name=endpoint_name, metric_name='InferenceSucceed')
    record_latency_metrics(start_time=sagemaker_out['start_time'],
                           ep_name=endpoint_name,
                           workflow=workflow,
                           metric_name='InferenceLatency')
