import json
import logging
import os

import boto3
from aws_lambda_powertools import Tracer
from common.sns_util import send_message_to_sns

tracer = Tracer()
s3_resource = boto3.resource('s3')

SNS_TOPIC = os.environ['NOTICE_SNS_TOPIC']

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)


# TODO
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

    if invocation_status != "Completed":
        # TODO update execute ddb status 失败
        print(f"Not complete invocation!")
        send_message_to_sns(message, SNS_TOPIC)
        return message

    endpoint_name = message["requestParameters"]["endpointName"]
    output_location = message["responseParameters"]["outputLocation"]
    # TODO 将结果写入ddb中 sg的 output path
