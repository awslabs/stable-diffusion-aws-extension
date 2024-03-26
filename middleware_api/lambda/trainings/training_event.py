import json
import logging
import os

import boto3

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok, not_found
from common.util import publish_msg
from libs.common_tools import split_s3_path
from libs.data_types import TrainJob, TrainJobStatus, CheckPoint, CheckPointStatus

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

train_table = os.environ.get('TRAINING_JOB_TABLE')
checkpoint_table = os.environ.get('CHECKPOINT_TABLE')
user_topic_arn = os.environ.get('USER_EMAIL_TOPIC_ARN')

sagemaker = boto3.client('sagemaker')
s3 = boto3.client('s3')

ddb_service = DynamoDbUtilsService(logger=logger)


def handler(event, ctx):
    logger.info(json.dumps(event))
    train_job_name = event['detail']['TrainingJobName']

    rows = ddb_service.scan(train_table, filters={
        'sagemaker_train_name': train_job_name,
    })

    logger.info(rows)

    if not rows or len(rows) == 0:
        return not_found(message=f'training job {train_job_name} is not found')

    training_job = TrainJob(**(ddb_service.deserialize(rows[0])))

    logger.info(training_job)

    check_status(training_job)

    return ok()


# sfn
def check_status(training_job: TrainJob):
    resp = sagemaker.describe_training_job(
        TrainingJobName=training_job.sagemaker_train_name
    )

    logger.info(resp)

    training_job_status = resp['TrainingJobStatus']
    secondary_status = resp['SecondaryStatus']

    ddb_service.update_item(
        table=train_table,
        key={'id': training_job.id},
        field_name='job_status',
        value=secondary_status
    )

    if training_job_status == 'Failed' or training_job_status == 'Stopped':
        if 'FailureReason' in resp:
            err_msg = resp['FailureReason']
            training_job.params['resp'] = {
                'status': 'Failed',
                'error_msg': err_msg,
                'raw_resp': resp
            }

    if training_job_status == 'Completed':

        try:
            notify_user(training_job)
        except Exception as e:
            logger.error(e)

        # todo: update checkpoints
        raw_checkpoint = ddb_service.get_item(table=checkpoint_table, key_values={
            'id': training_job.checkpoint_id
        })
        if raw_checkpoint is None or len(raw_checkpoint) == 0:
            # todo: or create new one
            return 'failed because no checkpoint, not normal'

        checkpoint = CheckPoint(**raw_checkpoint)
        checkpoint.checkpoint_status = CheckPointStatus.Active

        bucket, key = split_s3_path(checkpoint.s3_location)
        s3_resp = s3.list_objects(
            Bucket=bucket,
            Prefix=key,
        )
        checkpoint.checkpoint_names = []
        if 'Contents' in s3_resp and len(s3_resp['Contents']) > 0:
            for obj in s3_resp['Contents']:
                checkpoint_name = obj['Key'].replace(f'{key}/', "")
                checkpoint.checkpoint_names.append(checkpoint_name)
        else:
            checkpoint.checkpoint_status = CheckPointStatus.Initial
            ddb_service.update_item(
                table=train_table,
                key={'id': training_job.id},
                field_name='job_status',
                value=TrainJobStatus.Fail
            )

        ddb_service.update_item(
            table=checkpoint_table,
            key={
                'id': checkpoint.id
            },
            field_name='checkpoint_status',
            value=checkpoint.checkpoint_status.value
        )

        ddb_service.update_item(
            table=checkpoint_table,
            key={
                'id': checkpoint.id
            },
            field_name='checkpoint_names',
            value=checkpoint.checkpoint_names
        )

        training_job.params['resp'] = {
            'raw_resp': resp
        }

    ddb_service.update_item(
        table=train_table,
        key={'id': training_job.id},
        field_name='params',
        value=training_job.params
    )

    return


def notify_user(train_job: TrainJob):
    publish_msg(
        topic_arn=user_topic_arn,
        subject=f'Create Model Job {train_job.sagemaker_train_name} {train_job.job_status}',
        msg=f'to be done with resp: \n {train_job.job_status}'
    )  # todo: find out msg

    return 'job completed'
