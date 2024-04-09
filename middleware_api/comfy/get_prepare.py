import logging
import os

import boto3
from boto3.dynamodb.conditions import Key
from aws_lambda_powertools import Tracer

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok, no_content
from libs.utils import response_error

tracer = Tracer()
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

region = os.environ.get('AWS_REGION')
bucket_name = os.environ.get('S3_BUCKET_NAME')

inference_monitor_table = os.environ.get('INSTANCE_MONITOR_TABLE')
sync_table = os.environ.get('SYNC_TABLE')
config_table = os.environ.get('CONFIG_TABLE')

ddb_service = DynamoDbUtilsService(logger=logger)


dynamodb = boto3.resource('dynamodb')
sync_table = dynamodb.Table(sync_table)


def get_last_ddb_sync_record(endpoint_name):
    sync_response = sync_table.query(
        KeyConditionExpression=Key('endpoint_name').eq(endpoint_name),
        Limit=1,
        ScanIndexForward=False
    )
    latest_sync_record = sync_response['Items'][0] if ('Items' in sync_response
                                                       and len(sync_response['Items']) > 0) else None
    if latest_sync_record:
        logger.info(f"latest_sync_record is：{latest_sync_record}")
        return latest_sync_record

    logger.info("no latest_sync_record found")
    return None


def check_sync_and_instance_from_ddb(endpoint_name):
    sync_record = get_last_ddb_sync_record(endpoint_name)
    logger.debug(f'sync_record is : {sync_record}')
    if sync_record is None or len(sync_record) == 0:
        logger.info("No sync record for check_sync_and_instance_from_ddb return False")
        return False
    instance_count = int(sync_record['instance_count'])
    instance_monitor_records_resp = ddb_service.query_items(inference_monitor_table,
                                                            key_values={"endpoint_name": endpoint_name})
    logger.info(instance_monitor_records_resp)
    if (instance_monitor_records_resp is None):
        logger.info(f"No instance record for check_sync_and_instance_from_ddb return False")
        logger.debug(f" {instance_monitor_records_resp}")
        return False
    if len(instance_monitor_records_resp) < instance_count:
        logger.info(f"No enough instance record for check_sync_and_instance_from_ddb return False")
        logger.debug(f" {instance_monitor_records_resp} {sync_record}")
        return False
    logger.info(f"check_sync_and_instance_from_ddb return True")
    return True


@tracer.capture_lambda_handler
def handler(event, ctx):
    try:
        logger.info(f"get prepare start... Received event: {event}")
        logger.info(f"Received ctx: {ctx}")
        if 'pathParameters' not in event or not event['pathParameters'] or not event['pathParameters']['id']:
            return no_content()
        endpoint_name = event['pathParameters']['id']
        sync_success = check_sync_and_instance_from_ddb(endpoint_name)
        logger.info(f"get prepare end... response: {sync_success}")
        return ok(data={"prepareSuccess": sync_success})
    except Exception as e:
        return response_error(e)
