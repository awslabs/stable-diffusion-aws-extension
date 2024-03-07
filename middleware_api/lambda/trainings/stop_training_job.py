import json
import logging
import os

from common.const import PERMISSION_TRAIN_ALL
from common.ddb_service.client import DynamoDbUtilsService
from common.response import not_found, ok
from libs.data_types import TrainJob, TrainJobStatus
from libs.utils import permissions_check, response_error

train_table = os.environ.get('TRAIN_TABLE')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)


def handler(event, context):
    try:
        logger.info(json.dumps(event))
        train_job_id = event['pathParameters']['id']

        permissions_check(event, [PERMISSION_TRAIN_ALL])

        raw_train_job = ddb_service.get_item(table=train_table, key_values={
            'id': train_job_id
        })
        if raw_train_job is None or len(raw_train_job) == 0:
            return not_found(message=f'no such train job with id({train_job_id})')

        train_job = TrainJob(**raw_train_job)

        logger.info(f'train_job: {train_job}')

        ddb_service.update_item(
            table=train_table,
            key={'id': train_job_id},
            field_name='job_status',
            value=TrainJobStatus.Stopped.value
        )

        return ok()
    except Exception as e:
        return response_error(e)
