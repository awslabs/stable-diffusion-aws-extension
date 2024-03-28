import logging
import os

from aws_lambda_powertools import Tracer

from common.response import ok
from libs.utils import response_error

tracer = Tracer()
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

region = os.environ.get('AWS_REGION')
bucket_name = os.environ.get('S3_BUCKET_NAME')


@tracer.capture_lambda_handler
def handler(event, ctx):
    try:
        logger.info(f"get prepare start... Received event: {event}")
        logger.info(f"Received ctx: {ctx}")
        request_id = event['pathParameters']['id']
        response = None
        logger.info(f"get prepare end... response: {response}")
        return ok(data=response)
    except Exception as e:
        return response_error(e)
