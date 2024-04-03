import logging
import os

import boto3
from aws_lambda_powertools import Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from common.response import ok
from libs.utils import response_error

client = boto3.client('apigateway')

tracer = Tracer()

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)


@tracer.capture_lambda_handler
def handler(event: dict, context: LambdaContext):
    logger.info(f'event: {event}')
    logger.info(f'ctx: {context}')

    try:
        response = client.get_export(
            restApiId=event['requestContext']['apiId'],
            stageName='prod',
            exportType='oas30',
            parameters={'extensions': 'integrations'}
        )

        return ok(data=response, decimal=True)
    except Exception as e:

        return response_error(e)
