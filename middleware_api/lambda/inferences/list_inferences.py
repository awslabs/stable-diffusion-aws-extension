import json
import logging
import os

import boto3
from boto3.dynamodb.conditions import Key

from common.const import PERMISSION_INFERENCE_ALL
from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok, bad_request
from libs.data_types import InferenceJob
from libs.utils import get_user_roles, check_user_permissions, decode_last_key, encode_last_key, permissions_check, \
    response_error

inference_table_name = os.environ.get('INFERENCE_JOB_TABLE')
user_table = os.environ.get('MULTI_USER_TABLE')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)

ddb = boto3.resource('dynamodb')
table = ddb.Table(inference_table_name)


# GET /inferences?last_evaluated_key=xxx&limit=10&username=USER_NAME&name=SageMaker_Endpoint_Name&filter=key:value,key:value
def handler(event, ctx):
    logger.info(json.dumps(event))
    _filter = {}

    parameters = event['queryStringParameters']

    username = None
    limit = 10
    last_evaluated_key = None
    inference_type = "txt2img"

    try:
        permissions_check(event, [PERMISSION_INFERENCE_ALL])
        if parameters:
            username = parameters['username'] if 'username' in parameters and parameters['username'] else None
            limit = int(parameters['limit']) if 'limit' in parameters and parameters['limit'] else limit
            last_evaluated_key = parameters['last_evaluated_key'] if 'last_evaluated_key' in parameters and parameters[
                'last_evaluated_key'] else None
            inference_type = parameters['type'] if 'type' in parameters and parameters['type'] else inference_type

        scan_kwargs = {
            'Limit': limit,
            'IndexName': "taskType-createTime-index",
            'KeyConditionExpression': Key('taskType').eq(inference_type),
            "ScanIndexForward": False
        }

        if last_evaluated_key:
            scan_kwargs['ExclusiveStartKey'] = decode_last_key(last_evaluated_key)

        logger.info(scan_kwargs)

        response = table.query(**scan_kwargs)

        logger.info(json.dumps(response))

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

        data = {
            'inferences': results,
            'last_evaluated_key': last_evaluated_key
        }

        return ok(data=data, decimal=True)
    except Exception as e:
        return response_error(e)
