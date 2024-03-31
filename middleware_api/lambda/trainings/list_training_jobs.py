import json
import logging
import os

import boto3
from aws_lambda_powertools import Tracer

from common.const import PERMISSION_TRAIN_ALL
from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok
from common.util import get_query_param
from libs.data_types import TrainJob
from libs.utils import get_permissions_by_username, get_user_roles, check_user_permissions, permissions_check, \
    response_error, decode_last_key, encode_last_key

tracer = Tracer()
train_table = os.environ.get('TRAIN_TABLE')
user_table = os.environ.get('MULTI_USER_TABLE')
ddb = boto3.resource('dynamodb')
table = ddb.Table(train_table)
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)


# GET /trainings
@tracer.capture_lambda_handler
def handler(event, context):
    _filter = {}

    try:
        logger.info(json.dumps(event))
        requestor_name = permissions_check(event, [PERMISSION_TRAIN_ALL])

        exclusive_start_key = get_query_param(event, 'exclusive_start_key')
        limit = int(get_query_param(event, 'limit', 10))

        scan_kwargs = {
            'Limit': limit,
        }

        if exclusive_start_key:
            scan_kwargs['ExclusiveStartKey'] = decode_last_key(exclusive_start_key)

        logger.info(scan_kwargs)

        response = table.scan(**scan_kwargs)

        logger.info(json.dumps(response, default=str))
        items = response.get('Items', [])

        last_evaluated_key = encode_last_key(response.get('LastEvaluatedKey'))

        if items is None or len(items) == 0:
            return ok(data={'trainings': []})

        requestor_permissions = get_permissions_by_username(ddb_service, user_table, requestor_name)
        requestor_roles = get_user_roles(ddb_service=ddb_service, user_table_name=user_table, username=requestor_name)

        train_jobs = []
        for row in items:
            train_job = TrainJob(**row)

            train_job_dto = {
                'id': train_job.id,
                'modelName': get_model_name(train_job.params),
                'status': train_job.job_status.value,
                'trainType': train_job.train_type,
                'created': train_job.timestamp,
                'sagemakerTrainName': train_job.sagemaker_train_name,
                'params': train_job.params,
            }
            if train_job.allowed_roles_or_users and check_user_permissions(train_job.allowed_roles_or_users,
                                                                           requestor_roles, requestor_name):
                train_jobs.append(train_job_dto)
            elif not train_job.allowed_roles_or_users and \
                    'user' in requestor_permissions and \
                    'all' in requestor_permissions['user']:
                # superuser can view the legacy data
                train_jobs.append(train_job_dto)

        train_jobs = sort_jobs(train_jobs)

        data = {
            'trainings': train_jobs,
            'last_evaluated_key': last_evaluated_key
        }

        return ok(data=data, decimal=True)
    except Exception as e:
        return response_error(e)


def sort_jobs(train_jobs):
    if len(train_jobs) == 0:
        return train_jobs

    return sorted(train_jobs, key=lambda x: x['created'], reverse=True)


def get_model_name(params):
    model_name = 'not_applied'

    try:
        model_name = params['config_params']['saving_arguments']['output_name']
        if model_name:
            model_name = f"{model_name}.safetensors"
    except Exception as e:
        logger.info(f"Failed to get output name: {e}")

    return model_name
