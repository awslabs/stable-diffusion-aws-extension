from sagemaker import Predictor
from sagemaker.predictor_async import AsyncPredictor
import json
import dataclasses
import datetime
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError

from common.response import ok, bad_request, internal_server_error
from common.util import publish_msg
from common_tools import complete_multipart_upload, split_s3_path, DecimalEncoder
from common.stepfunction_service.client import StepFunctionUtilsService
from common.ddb_service.client import DynamoDbUtilsService
from common_tools import get_base_model_s3_key, get_base_checkpoint_s3_key, \
    batch_get_s3_multipart_signed_urls

from _types import Model, CreateModelStatus, CheckPoint, CheckPointStatus, MultipartFileReq
from multi_users.utils import get_permissions_by_username, get_user_roles, check_user_permissions

bucket_name = os.environ.get('S3_BUCKET')
model_table = os.environ.get('DYNAMODB_TABLE')
checkpoint_table = os.environ.get('CHECKPOINT_TABLE')
endpoint_name = os.environ.get('SAGEMAKER_ENDPOINT_NAME')
user_table = os.environ.get('MULTI_USER_TABLE')

success_topic_arn = os.environ.get('SUCCESS_TOPIC_ARN')
error_topic_arn = os.environ.get('ERROR_TOPIC_ARN')
user_topic_arn = os.environ.get('USER_TOPIC_ARN')

logger = logging.getLogger('boto3')
logger.setLevel(logging.INFO)
ddb_service = DynamoDbUtilsService(logger=logger)
stepfunctions_client = StepFunctionUtilsService(logger=logger)


@dataclasses.dataclass
class Event:
    model_type: str
    name: str
    params: dict[str, Any]
    filenames: [MultipartFileReq]
    creator: str
    checkpoint_id: Optional[str] = ""


# POST /model
def create_model_api(raw_event, context):
    logger.info(json.dumps(raw_event))
    request_id = context.aws_request_id
    event = Event(**json.loads(raw_event['body']))
    _type = event.model_type

    try:
        # check if roles has already linked to an endpoint?
        creator_permissions = get_permissions_by_username(ddb_service, user_table, event.creator)
        if 'train' not in creator_permissions \
                or ('all' not in creator_permissions['train'] and 'create' not in creator_permissions['train']):
            return bad_request(message=f'user {event.creator} has not permission to create a train job')

        user_roles = get_user_roles(ddb_service, user_table, event.creator)

        # todo: check if duplicated name and new_model_name only for Completed and Model
        if not event.checkpoint_id and len(event.filenames) == 0:
            return bad_request(message='either checkpoint_id or filenames need to be provided')

        base_key = get_base_model_s3_key(_type, event.name, request_id)
        timestamp = datetime.datetime.now().timestamp()
        multiparts_resp = {}
        if not event.checkpoint_id:
            checkpoint_base_key = get_base_checkpoint_s3_key(_type, event.name, request_id)
            presign_url_map = batch_get_s3_multipart_signed_urls(
                bucket_name=bucket_name,
                base_key=checkpoint_base_key,
                filenames=event.filenames
            )
            filenames_only = []
            for f in event.filenames:
                file = MultipartFileReq(**f)
                filenames_only.append(file.filename)

            checkpoint_params = {'created': str(datetime.datetime.now()), 'multipart_upload': {
            }}

            for key, val in presign_url_map.items():
                checkpoint_params['multipart_upload'][key] = {
                    'upload_id': val['upload_id'],
                    'bucket': val['bucket'],
                    'key': val['key'],
                }
                multiparts_resp[key] = val['s3_signed_urls']

            checkpoint = CheckPoint(
                id=request_id,
                checkpoint_type=event.model_type,
                s3_location=f's3://{bucket_name}/{get_base_checkpoint_s3_key(_type, event.name, request_id)}',
                checkpoint_names=filenames_only,
                checkpoint_status=CheckPointStatus.Initial,
                params=checkpoint_params,
                timestamp=timestamp,
                allowed_roles_or_users=user_roles,
            )
            ddb_service.put_items(table=checkpoint_table, entries=checkpoint.__dict__)
            checkpoint_id = checkpoint.id
        else:
            raw_checkpoint = ddb_service.get_item(table=checkpoint_table, key_values={
                'id': event.checkpoint_id,
            })
            if raw_checkpoint is None:
                return bad_request(message=f'create model ckpt with id {event.checkpoint_id} is not found')

            checkpoint = CheckPoint(**raw_checkpoint)
            if checkpoint.checkpoint_status != CheckPointStatus.Active:
                return bad_request(message=f'checkpoint with id ({checkpoint.id}) is not Active to use')
            checkpoint_id = checkpoint.id
            if checkpoint.allowed_roles_or_users:
                allowed_to_use = False
                for role in checkpoint.allowed_roles_or_users:
                    if role in user_roles or '*' == role:
                        allowed_to_use = True
                        break

                if not allowed_to_use:
                    return bad_request(message=f'checkpoint with id ({checkpoint.id}) is not allowed to use by user {event.creator}')

        model_job = Model(
            id=request_id,
            name=event.name,
            output_s3_location=f's3://{bucket_name}/{base_key}/output',
            checkpoint_id=checkpoint_id,
            model_type=_type,
            job_status=CreateModelStatus.Initial,
            params=event.params,
            timestamp=timestamp,
            allowed_roles_or_users=[event.creator]
        )
        ddb_service.put_items(table=model_table, entries=model_job.__dict__)

    except ClientError as e:
        logger.error(e)
        return internal_server_error(message=str(e))

    data = {
        'job': {
            'id': model_job.id,
            'status': model_job.job_status.value,
            's3_base': checkpoint.s3_location,
            'model_type': model_job.model_type,
            'params': model_job.params  # not safe if not json serializable type
        },
        's3PresignUrl':  multiparts_resp
    }

    return ok(data=data)


# GET /models
def list_all_models_api(event, context):
    _filter = {}

    parameters = event['queryStringParameters']
    if parameters:
        if 'types' in parameters and len(parameters['types']) > 0:
            _filter['model_type'] = parameters['types']

        if 'status' in parameters and len(parameters['status']) > 0:
            _filter['job_status'] = parameters['status']

    resp = ddb_service.scan(table=model_table, filters=_filter)

    if resp is None or len(resp) == 0:
        return ok(data={'models': []})

    models = []

    try:
        requestor_name = event['requestContext']['authorizer']['username']
        requestor_permissions = get_permissions_by_username(ddb_service, user_table, requestor_name)
        requestor_roles = get_user_roles(ddb_service=ddb_service, user_table_name=user_table, username=requestor_name)
        if 'train' not in requestor_permissions or \
                ('all' not in requestor_permissions['train'] and 'list' not in requestor_permissions['train']):
            return bad_request(message='user has no permission to train')

        for r in resp:
            model = Model(**(ddb_service.deserialize(r)))
            model_dto = {
                'id': model.id,
                'model_name': model.name,
                'created': model.timestamp,
                'params': model.params,
                'status': model.job_status.value,
                'output_s3_location': model.output_s3_location
            }
            if model.allowed_roles_or_users and check_user_permissions(model.allowed_roles_or_users, requestor_roles, requestor_name):
                models.append(model_dto)
            elif not model.allowed_roles_or_users and \
                    'user' in requestor_permissions and \
                    'all' in requestor_permissions['user']:
                # superuser can view the legacy data
                models.append(model_dto)

        return ok(data={'models': models}, decimal=True)
    except Exception as e:
        logger.error(e)
        return bad_request(message=str(e))


@dataclass
class PutModelEvent:
    model_id: str
    status: str
    multi_parts_tags: Dict[str, Any]


# PUT /model
def update_model_job_api(raw_event, context):
    logger.info(json.dumps(raw_event))
    event = PutModelEvent(**json.loads(raw_event['body']))

    model_id = raw_event['pathParameters']['id']

    try:
        raw_model_job = ddb_service.get_item(table=model_table, key_values={'id': model_id})
        if raw_model_job is None:
            return bad_request(message=f'create model with id {model_id} is not found')

        model_job = Model(**raw_model_job)
        raw_checkpoint = ddb_service.get_item(table=checkpoint_table, key_values={
            'id': model_job.checkpoint_id,
        })
        if raw_checkpoint is None:
            return bad_request(message=f'create model ckpt with id {model_id} is not found')

        ckpt = CheckPoint(**raw_checkpoint)
        if ckpt.checkpoint_status == ckpt.checkpoint_status.Initial:
            complete_multipart_upload(ckpt, event.multi_parts_tags)
            ddb_service.update_item(
                table=checkpoint_table,
                key={'id': ckpt.id},
                field_name='checkpoint_status',
                value=CheckPointStatus.Active.value
            )

        resp = _exec(model_job, CreateModelStatus[event.status])
        ddb_service.update_item(
            table=model_table,
            key={'id': model_job.id},
            field_name='job_status',
            value=event.status
        )
        return ok(data=resp)
    except ClientError as e:
        logger.error(e)
        return internal_server_error(message=str(e))


# SNS callback
def process_result(event, context):
    records = event['Records']
    for record in records:
        msg_str = record['Sns']['Message']
        print(msg_str)
        msg = json.loads(msg_str)
        inference_id = msg['inferenceId']

        model_job_raw = ddb_service.get_item(table=model_table, key_values={
            'id': inference_id
        })
        if model_job_raw is None:
            return {
                'statusCode': '500',
                'error': f'id with {inference_id} not found'
            }
        model = Model(**model_job_raw)

        if record['Sns']['TopicArn'] == success_topic_arn:
            resp_location = msg['responseParameters']['outputLocation']
            bucket, key = split_s3_path(resp_location)
            content = get_object(bucket=bucket, key=key)
            if content['statusCode'] != 200:
                ddb_service.update_item(
                    table=model_table,
                    key={'id': model.id},
                    field_name='job_status',
                    value=CreateModelStatus.Fail.value
                )
                publish_msg(
                    topic_arn=user_topic_arn,
                    subject=f'Create Model Job {model.name}: {model.id} failed',
                    msg='to be done'
                )  # todo: find out msg
                return

            msgs = content['message']
            model.params['resp'] = {}
            for key, val in msgs.items():
                model.params['resp'][key] = val

            ddb_service.update_item(
                table=model_table,
                key={'id': inference_id},
                field_name='job_status',
                value=CreateModelStatus.Complete.value
            )
            params = model_job_raw['params']
            params['resp']['s3_output_location'] = f'{bucket_name}/{model.model_type}/{model.name}.tar'
            ddb_service.update_item(
                table=model_table,
                key={'id': inference_id},
                field_name='params',
                value=params
            )

            publish_msg(
                topic_arn=user_topic_arn,
                subject=f'Create Model Job {model.name}: {model.id} success',
                msg=f'model {model.name}: {model.id} is ready to use'
            )  # todo: find out msg

        if record['Sns']['TopicArn'] == error_topic_arn:
            ddb_service.update_item(
                table=model_table,
                key={'id': inference_id},
                field_name='job_status',
                value=CreateModelStatus.Fail.value
            )
            publish_msg(
                topic_arn=user_topic_arn,
                subject=f'Create Model Job {model.name}: {model.id} failed',
                msg='to be done'
            )  # todo: find out msg
    return {
        'statusCode': 200,
        'msg': f'finished events {event}'
    }


def get_object(bucket: str, key: str):
    s3_client = boto3.client('s3')
    data = s3_client.get_object(Bucket=bucket, Key=key)
    content = json.load(data['Body'])
    return content


def _exec(model_job: Model, action: CreateModelStatus):
    if model_job.job_status == CreateModelStatus.Creating and \
            (action != CreateModelStatus.Fail or action != CreateModelStatus.Complete):
        raise Exception(f'model creation job is currently under progress, so cannot be updated')

    if action == CreateModelStatus.Creating:
        model_job.job_status = action
        raw_chkpt = ddb_service.get_item(table=checkpoint_table, key_values={'id': model_job.checkpoint_id})
        if raw_chkpt is None:
            return {
                'statusCode': 200,
                'error': f'model related checkpoint with id {model_job.checkpoint_id} is not found'
            }

        checkpoint = CheckPoint(**raw_chkpt)
        checkpoint.checkpoint_status = CheckPointStatus.Active
        ddb_service.update_item(
            table=checkpoint_table,
            key={'id': checkpoint.id},
            field_name='checkpoint_status',
            value=CheckPointStatus.Active.value
        )
        return create_sagemaker_inference(job=model_job, checkpoint=checkpoint)
    elif action == CreateModelStatus.Initial:
        raise Exception('please create a new model creation job for this,'
                        f' not allowed overwrite old model creation job')
    else:
        # todo: other action
        raise NotImplemented


def create_sagemaker_inference(job: Model, checkpoint: CheckPoint):
    payload = {
        "task": "db-create-model",  # router
        "param_s3": "",
        "db_create_model_payload": json.dumps({
            "s3_output_path": job.output_s3_location,  # output object
            "s3_input_path": checkpoint.s3_location,
            "ckpt_names": checkpoint.checkpoint_names,
            "param": job.params,
            "job_id": job.id
        }, cls=DecimalEncoder),
    }

    from sagemaker.serializers import JSONSerializer
    from sagemaker.deserializers import JSONDeserializer

    predictor = Predictor(endpoint_name)

    predictor = AsyncPredictor(predictor, name=job.id)
    predictor.serializer = JSONSerializer()
    predictor.deserializer = JSONDeserializer()
    prediction = predictor.predict_async(data=payload, inference_id=job.id)
    output_path = prediction.output_path

    return {
        'statusCode': 200,
        'job': {
            'output_path': output_path,
            'id': job.id,
            'endpointName': endpoint_name,
            'jobStatus': job.job_status.value,
            'jobType': job.model_type
        }
    }


