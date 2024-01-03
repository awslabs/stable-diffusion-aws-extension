import json
import logging
import os

import boto3

from common.ddb_service.client import DynamoDbUtilsService
from common.response import not_found, bad_request, ok
from libs.data_types import TrainJob, TrainJobStatus

train_table = os.environ.get('TRAIN_TABLE')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)

sfn_client = boto3.client('stepfunctions')


def handler(event, context):
    logger.info(json.dumps(event))
    train_job_id = event['pathParameters']['id']

    return _stop_train_job(train_job_id)


def _stop_train_job(train_job_id: str):
    raw_train_job = ddb_service.get_item(table=train_table, key_values={
        'id': train_job_id
    })
    if raw_train_job is None or len(raw_train_job) == 0:
        return not_found(message=f'no such train job with id({train_job_id})')

    train_job = TrainJob(**raw_train_job)

    logger.info(f'train_job: {train_job}')

    try:

        if train_job.sagemaker_sfn_arn:
            sfn_client.stop_execution(
                executionArn=train_job.sagemaker_sfn_arn,
                error='user stop',
                cause='Explanation about why the execution is being stopped'
            )

        ddb_service.update_item(
            table=train_table,
            key={'id': train_job_id},
            field_name='job_status',
            value=TrainJobStatus.Stopped.value
        )

        return ok()
    except Exception as e:
        print(e)
        return bad_request(message=str(e))
