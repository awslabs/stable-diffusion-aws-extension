import logging
import os

from aws_lambda_powertools import Tracer

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok, not_found
from common.util import generate_presigned_url_for_job, generate_presigned_url_for_keys
from libs.comfy_data_types import ComfyExecuteTable
from libs.utils import response_error

tracer = Tracer()
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

execute_table = os.environ.get('EXECUTE_TABLE')
ddb_service = DynamoDbUtilsService(logger=logger)


@tracer.capture_lambda_handler
def handler(event, ctx):
    try:
        logger.info(f"get execute start... Received event: {event}")
        logger.info(f"Received ctx: {ctx}")
        prompt_id = event['pathParameters']['id']

        item = ddb_service.get_item(table=execute_table, key_values={"prompt_id": prompt_id})
        logger.info(item)

        if not item:
            return not_found(f"execute not found for prompt_id: {prompt_id}")

        if 'output_path' in item and 'output_files' in item and item['output_path'] and item['output_files']:
            item['output_files'] = generate_presigned_url_for_keys(item['output_path'], item['output_files'])

        if 'temp_path' in item and 'temp_files' in item and item['temp_path'] and item['temp_files']:
            item['temp_files'] = generate_presigned_url_for_keys(item['temp_path'], item['temp_files'])

        job = ComfyExecuteTable(**item)
        if not job.output_files:
            job.output_files = []

        if not job.temp_files:
            job.temp_files = []

        return ok(data=item, decimal=True)
    except Exception as e:
        return response_error(e)
