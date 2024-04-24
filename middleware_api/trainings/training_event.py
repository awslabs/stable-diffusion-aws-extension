import datetime
import json
import logging
import os
import uuid

import boto3
from aws_lambda_powertools import Tracer

from common import const
from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok, not_found
from common.util import publish_msg
from libs.data_types import TrainJob, TrainJobStatus, CheckPoint, CheckPointStatus

tracer = Tracer()
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

train_table = os.environ.get('TRAINING_JOB_TABLE')
checkpoint_table = os.environ.get('CHECKPOINT_TABLE')
user_topic_arn = os.environ.get('USER_EMAIL_TOPIC_ARN')
bucket_name = os.environ.get("S3_BUCKET_NAME")
sagemaker = boto3.client('sagemaker')
s3 = boto3.client('s3')

ddb_service = DynamoDbUtilsService(logger=logger)


@tracer.capture_lambda_handler
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
            logger.error(e, exc_info=True)

        prefix = f"Stable-diffusion/checkpoint/custom/{training_job.id}"
        s3_resp = s3.list_objects(
            Bucket=bucket_name,
            Prefix=prefix,
        )

        if 'Contents' in s3_resp and len(s3_resp['Contents']) > 0:
            for obj in s3_resp['Contents']:
                checkpoint_name = obj['Key'].replace(f'{prefix}/', "")
                logger.info(f'checkpoint_name: {checkpoint_name}')
                insert_ckpt(checkpoint_name, training_job)

                logs = get_logs(training_job.id)
                ddb_service.update_item(
                    table=train_table,
                    key={'id': training_job.id},
                    field_name='logs',
                    value=logs
                )

        else:
            ddb_service.update_item(
                table=train_table,
                key={'id': training_job.id},
                field_name='job_status',
                value=TrainJobStatus.Fail
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


def get_logs(job_id: str):
    prefix = f"kohya/train/{job_id}/logs/"
    s3_resp = s3.list_objects(
        Bucket=bucket_name,
        Prefix=prefix,
    )

    logs = []
    if 'Contents' in s3_resp and len(s3_resp['Contents']) > 0:
        for obj in s3_resp['Contents']:
            logs.append({
                'filename': obj['Key'].replace(prefix, ''),
                'Key': obj['Key']
            })

    return logs


def insert_ckpt(output_name, job: TrainJob):
    raw_ckpts = ddb_service.scan(checkpoint_table)
    for r in raw_ckpts:
        ckpt = CheckPoint(**(ddb_service.deserialize(r)))
        if output_name in ckpt.checkpoint_names:
            return

    checkpoint = CheckPoint(
        id=str(uuid.uuid4()),
        checkpoint_type=const.CheckPointType.LORA,
        checkpoint_names=[output_name],
        s3_location=f"s3://{bucket_name}/Stable-diffusion/checkpoint/custom/{job.id}",
        checkpoint_status=CheckPointStatus.Active,
        timestamp=datetime.datetime.now().timestamp(),
        allowed_roles_or_users=job.allowed_roles_or_users,
    )

    ddb_service.put_items(table=checkpoint_table, entries=checkpoint.__dict__)


def notify_user(train_job: TrainJob):
    publish_msg(
        topic_arn=user_topic_arn,
        subject=f'Create Model Job {train_job.sagemaker_train_name} {train_job.job_status}',
        msg=f'to be done with resp: \n {train_job.job_status}'
    )  # todo: find out msg

    return 'job completed'
