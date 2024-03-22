import logging
import os

from response import ok

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

region = os.environ.get('AWS_REGION')
bucket_name = os.environ.get('BUCKET_NAME')


def handler(event, ctx):
    logger.info(f"get prepare start... Received event: {event}")
    logger.info(f"Received ctx: {ctx}")
    request_id = event['pathParameters']['id']
    response = None
    logger.info(f"get prepare end... response: {response}")
    return ok(data=response)
