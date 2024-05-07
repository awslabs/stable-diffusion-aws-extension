import logging
import os
import time
from datetime import datetime, timedelta

import boto3
from aws_lambda_powertools import Tracer

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok, not_found
from libs.comfy_data_types import ComfyExecuteTable
from libs.utils import response_error

tracer = Tracer()
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)
ddb = boto3.resource('dynamodb')
client = boto3.client('logs')
ddb_service = DynamoDbUtilsService(logger=logger)

execute_table = os.environ.get('EXECUTE_TABLE')


@tracer.capture_lambda_handler
def handler(event, ctx):
    try:
        logger.info(f"Received ctx: {ctx}")
        prompt_id = event['pathParameters']['id']

        item = ddb_service.get_item(table=execute_table, key_values={"prompt_id": prompt_id})
        logger.info(item)

        if not item:
            return not_found(f"execute not found for prompt_id: {prompt_id}")

        job = ComfyExecuteTable(**item)
        logger.info(job)

        query = f"""
        fields @timestamp, @message, @logStream
        | filter @message like /{prompt_id}/
        | sort @timestamp asc
        | limit 1000
        """

        dt = datetime.strptime(job.start_time, '%Y-%m-%dT%H:%M:%S.%f')
        response = client.start_query(
            logGroupName=f'/aws/sagemaker/Endpoints/{job.endpoint_name}',
            startTime=int(dt.timestamp()),
            endTime=int((dt + timedelta(hours=1)).timestamp()),
            queryString=query,
            limit=1000
        )

        query_id = response['queryId']

        # Wait for the query to complete
        while True:
            query_status = client.get_query_results(
                queryId=query_id
            )
            status = query_status['status']
            if status == 'Complete':
                break
            elif status == 'Failed' or status == 'Cancelled':
                print("Query failed or was cancelled")
                break
            time.sleep(1)

        results = []
        for result in query_status['results']:
            item = {field['field']: field['value'] for field in result}
            results.append({
                'timestamp': item["@timestamp"],
                'message': item["@message"],
                'logStream': item["@logStream"],
            })

        return ok(data={'results': results}, decimal=True)
    except Exception as e:
        return response_error(e)
