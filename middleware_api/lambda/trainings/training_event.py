import json
import logging
import os

import boto3

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok
from common.util import publish_msg
from libs.common_tools import split_s3_path

from libs.data_types import TrainJob, TrainJobStatus, CheckPoint, CheckPointStatus

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')

train_table = dynamodb.Table(os.environ.get('TRAINING_JOB_TABLE'))
checkpoint_table = dynamodb.Table(os.environ.get('CHECKPOINT_TABLE'))
user_topic_arn = os.environ.get('USER_EMAIL_TOPIC_ARN')

sagemaker = boto3.client('sagemaker')
s3 = boto3.client('s3')

ddb_service = DynamoDbUtilsService(logger=logger)



def handler(event, ctx):
    logger.info(json.dumps(event))

    return ok()

# sfn
def check_status(event, context):
    train_job_name = event['train_job_name']
    train_job_id = event['train_job_id']

    resp = sagemaker.describe_training_job(
        TrainingJobName=train_job_name
    )

    training_job_status = resp['TrainingJobStatus']
    event['status'] = training_job_status

    raw_train_job = ddb_service.get_item(table=train_table, key_values={
        'id': train_job_id,
    })

    if raw_train_job is None or len(raw_train_job) == 0:
        event['status'] = 'Failed'
        return {
            'statusCode': 500,
            'msg': f'no such training job find in ddb id[{train_job_id}]'
        }

    training_job = TrainJob(**raw_train_job)
    if training_job_status == 'InProgress' or training_job_status == 'Stopping':
        return event

    if training_job_status == 'Failed' or training_job_status == 'Stopped':
        training_job.job_status = TrainJobStatus.Fail
        if 'FailureReason' in resp:
            err_msg = resp['FailureReason']
            training_job.params['resp'] = {
                'status': 'Failed',
                'error_msg': err_msg,
                'raw_resp': resp
            }

    if training_job_status == 'Completed':
        training_job.job_status = TrainJobStatus.Complete
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
            training_job.job_status = TrainJobStatus.Fail
            checkpoint.checkpoint_status = CheckPointStatus.Initial

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

    # fixme: this is ugly
    ddb_service.update_item(
        table=train_table,
        key={'id': training_job.id},
        field_name='job_status',
        value=training_job.job_status.value
    )

    ddb_service.update_item(
        table=train_table,
        key={'id': training_job.id},
        field_name='params',
        value=training_job.params
    )

    return event


def notify_user(event):
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
