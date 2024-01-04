import logging
import os

from common.ddb_service.client import DynamoDbUtilsService
from common.util import publish_msg
from libs.data_types import TrainJob

train_table = os.environ.get('TRAIN_TABLE')
user_topic_arn = os.environ.get('USER_EMAIL_TOPIC_ARN')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)


# sfn
def handler(event, context):
    train_job_id = event['train_job_id']

    raw_train_job = ddb_service.get_item(table=train_table, key_values={
        'id': train_job_id,
    })

    if raw_train_job is None or len(raw_train_job) == 0:
        return {
            'statusCode': 500,
            'msg': f'no such training job find in ddb id[{train_job_id}]'
        }

    train_job = TrainJob(**raw_train_job)

    publish_msg(
        topic_arn=user_topic_arn,
        subject=f'Create Model Job {train_job.sagemaker_train_name} {train_job.job_status}',
        msg=f'to be done with resp: \n {train_job.job_status}'
    )  # todo: find out msg

    return 'job completed'
