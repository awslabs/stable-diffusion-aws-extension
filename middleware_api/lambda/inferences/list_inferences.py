import json
import logging
import os

import boto3
from aws_lambda_powertools import Tracer
from boto3.dynamodb.conditions import Key

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok
from common.util import get_query_param
from libs.data_types import InferenceJob
from libs.utils import get_user_roles, check_user_permissions, decode_last_key, encode_last_key, response_error

tracer = Tracer()

inference_table_name = os.environ.get('INFERENCE_JOB_TABLE')
user_table = os.environ.get('MULTI_USER_TABLE')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)

ddb = boto3.resource('dynamodb')
table = ddb.Table(inference_table_name)


# GET /inferences?last_evaluated_key=xxx&limit=10
@tracer.capture_lambda_handler
def handler(event, ctx):
    try:
        logger.info(json.dumps(event))
        _filter = {}

        # todo compatibility with old version
        # permissions_check(event, [PERMISSION_INFERENCE_ALL])

        username = get_query_param(event, 'username')
        exclusive_start_key = get_query_param(event, 'exclusive_start_key')
        inference_type = get_query_param(event, 'type', 'txt2img')
        limit = int(get_query_param(event, 'limit', 10))

        scan_kwargs = {
            'Limit': limit,
            'IndexName': "taskType-createTime-index",
            'KeyConditionExpression': Key('taskType').eq(inference_type),
            "ScanIndexForward": False
        }

        if exclusive_start_key:
            scan_kwargs['ExclusiveStartKey'] = decode_last_key(exclusive_start_key)

        logger.info(scan_kwargs)

        response = table.query(**scan_kwargs)

        logger.info(json.dumps(response, default=str))

        items = response.get('Items', [])
        last_evaluated_key = encode_last_key(response.get('LastEvaluatedKey'))

        results = []
        user_roles = []
        if username:
            user_roles = get_user_roles(ddb_service=ddb_service, user_table_name=user_table, username=username)

        for row in items:
            inference = InferenceJob(**row)
            if username:
                if check_user_permissions(inference.owner_group_or_role, user_roles, username):
                    results.append(inference.__dict__)
            else:
                results.append(inference.__dict__)

        results = sort_inferences(results)

        data = {
            'inferences': results,
            'last_evaluated_key': last_evaluated_key
        }

        return ok(data=data, decimal=True)
    except Exception as e:
        return response_error(e)


def sort_inferences(data):
    if len(data) == 0:
        return data

    return sorted(data, key=lambda x: x['createTime'], reverse=True)
