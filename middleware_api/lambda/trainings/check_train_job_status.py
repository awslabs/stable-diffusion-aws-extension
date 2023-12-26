import logging
import os

import boto3

from common.ddb_service.client import DynamoDbUtilsService
from libs.common_tools import split_s3_path
from libs.data_types import TrainJob, TrainJobStatus, CheckPoint, CheckPointStatus

train_table = os.environ.get('TRAIN_TABLE')
checkpoint_table = os.environ.get('CHECKPOINT_TABLE')
logger = logging.getLogger('boto3')
logger.setLevel(logging.INFO)
ddb_service = DynamoDbUtilsService(logger=logger)
boto3_sagemaker = boto3.client('sagemaker')
s3 = boto3.client('s3')


# sfn
def handler(event, context):
    train_job_name = event['train_job_name']
    train_job_id = event['train_job_id']

    resp = boto3_sagemaker.describe_training_job(
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
