import dataclasses
import json
import logging
import os
import random
from datetime import datetime
from typing import List, Any, Optional

from sagemaker import Predictor
from sagemaker.deserializers import JSONDeserializer
from sagemaker.predictor_async import AsyncPredictor
from sagemaker.serializers import JSONSerializer

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok, bad_request
from common.util import generate_presign_url, load_json_from_s3, upload_json_to_s3, split_s3_path
from common.types import CheckPoint, CheckPointStatus
from common.types import InferenceJob, InvocationsRequest, EndpointDeploymentJob
from common.utils import get_user_roles, check_user_permissions

bucket_name = os.environ.get('S3_BUCKET')
checkpoint_table = os.environ.get('CHECKPOINT_TABLE')
sagemaker_endpoint_table = os.environ.get('DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME')
inference_table_name = os.environ.get('DDB_INFERENCE_TABLE_NAME')
user_table = os.environ.get('MULTI_USER_TABLE')

logger = logging.getLogger('inference_v2')
ddb_service = DynamoDbUtilsService(logger=logger)


@dataclasses.dataclass
class PrepareEvent:
    task_type: str
    models: dict[str, List[str]]  # [checkpoint_type: names] this is same as checkpoint if confused
    filters: dict[str, Any]
    sagemaker_endpoint_name: Optional[str] = ""
    user_id: Optional[str] = ""


# POST /inference/v2
def prepare_inference(raw_event, context):
    request_id = context.aws_request_id
    event = PrepareEvent(**json.loads(raw_event['body']))
    _type = event.task_type

    try:
        extra_generate_types = ['extra-single-image', 'extra-batch-images', 'rembg']
        simple_generate_types = ['txt2img', 'img2img']

        if _type not in simple_generate_types and _type not in extra_generate_types:
            return bad_request(
                message=f'task type {event.task_type} should be in {extra_generate_types} or {simple_generate_types}'
            )

        # check if endpoint table for endpoint status and existence
        inference_endpoint = _schedule_inference_endpoint(event.sagemaker_endpoint_name, event.user_id)
        endpoint_name = inference_endpoint.endpoint_name
        endpoint_id = inference_endpoint.EndpointDeploymentJobId

        # generate param s3 location for upload
        param_s3_key = f'{get_base_inference_param_s3_key(_type, request_id)}/api_param.json'
        s3_location = f's3://{bucket_name}/{param_s3_key}'
        presign_url = generate_presign_url(bucket_name, param_s3_key)
        inference_job = InferenceJob(
            InferenceJobId=request_id,
            startTime=str(datetime.now()),
            status='created',
            taskType=_type,
            owner_group_or_role=[event.user_id],
            params={
                'input_body_s3': s3_location,
                'input_body_presign_url': presign_url,
                'sagemaker_inference_endpoint_id': endpoint_id,
                'sagemaker_inference_endpoint_name': endpoint_name,
            },
        )
        resp = {
            'inference': {
                'id': request_id,
                'type': _type,
                'api_params_s3_location': s3_location,
                'api_params_s3_upload_url': presign_url,
            }
        }

        if _type in simple_generate_types:
            # check if model(checkpoint) path(s) exists. return error if not
            ckpts = []
            ckpts_to_upload = []
            for ckpt_type, names in event.models.items():
                for name in names:
                    ckpt = _get_checkpoint_by_name(name, ckpt_type)
                    # todo: need check if user has permission for the model
                    if ckpt is None:
                        ckpts_to_upload.append({
                            'name': name,
                            'ckpt_type': ckpt_type
                        })
                    else:
                        ckpts.append(ckpt)

            if len(ckpts_to_upload) > 0:
                message = [f'checkpoint with name {c["name"]}, type {c["ckpt_type"]} is not found' for c in
                           ckpts_to_upload]
                return bad_request(message=' '.join(message))

            # create inference job with param location in ddb, status set to Created
            used_models = {}
            for ckpt in ckpts:
                if ckpt.checkpoint_type not in used_models:
                    used_models[ckpt.checkpoint_type] = []

                used_models[ckpt.checkpoint_type].append(
                    {
                        'id': ckpt.id,
                        'model_name': ckpt.checkpoint_names[0],
                        's3': ckpt.s3_location,
                        'type': ckpt.checkpoint_type
                    }
                )

            inference_job.params['used_models'] = used_models
            resp['inference']['models'] = [{'id': ckpt.id, 'name': ckpt.checkpoint_names, 'type': ckpt.checkpoint_type}
                                           for ckpt in ckpts]

        ddb_service.put_items(inference_table_name, entries=inference_job.__dict__)
        return ok(data=resp)
    except Exception as e:
        return bad_request(message=str(e))


# PUT /v2/inference/{inference_id}/run
def run_inference(event, _):
    _filter = {}
    inference_id = event['pathParameters']['id']

    # get the inference job from ddb by job id
    inference_raw = ddb_service.get_item(inference_table_name, {
        'InferenceJobId': inference_id
    })

    assert inference_raw is not None and len(inference_raw) > 0
    inference_job = InferenceJob(**inference_raw)
    endpoint_name = inference_job.params['sagemaker_inference_endpoint_name']
    models = {}
    if 'used_models' in inference_job.params:
        models = {
            "space_free_size": 4e10,
            **inference_job.params['used_models'],
        }

    payload = InvocationsRequest(
        task=inference_job.taskType,
        username="test",
        models=models,
        param_s3=inference_job.params['input_body_s3']
    )

    # start async inference
    predictor = Predictor(endpoint_name)
    initial_args = {"InvocationTimeoutSeconds": 3600}
    predictor = AsyncPredictor(predictor, name=endpoint_name)
    predictor.serializer = JSONSerializer()
    predictor.deserializer = JSONDeserializer()
    prediction = predictor.predict_async(data=payload.__dict__, initial_args=initial_args, inference_id=inference_id)
    output_path = prediction.output_path

    # update the ddb job status to 'inprogress' and save to ddb
    inference_job.status = 'inprogress'
    inference_job.params['output_path'] = output_path
    ddb_service.put_items(inference_table_name, inference_job.__dict__)

    data = {
        'inference': {
            'inference_id': inference_id,
            'status': inference_job.status,
            'endpoint_name': endpoint_name,
            'output_path': output_path
        }
    }

    return ok(data=data)


# GET /inferences?last_evaluated_key=xxx&limit=10&username=USER_NAME&name=SageMaker_Endpoint_Name&filter=key:value,key:value
def list_all_inference_jobs(event, ctx):
    _filter = {}

    parameters = event['queryStringParameters']

    # todo: support pagination later
    # limit = parameters['limit'] if 'limit' in parameters and parameters['limit'] else None
    # last_evaluated_key = parameters['last_evaluated_key'] if 'last_evaluated_key' in parameters and parameters[
    #     'last_evaluated_key'] else None
    #
    # if last_evaluated_key and isinstance(last_evaluated_key, str):
    #     last_evaluated_key = json.loads(last_evaluated_key)
    # last_token = None

    username = None
    if parameters:
        username = parameters['username'] if 'username' in parameters and parameters['username'] else None

    scan_rows = ddb_service.scan(inference_table_name, filters=None)
    results = []
    user_roles = []
    if username:
        user_roles = get_user_roles(ddb_service=ddb_service, user_table_name=user_table, username=username)

    for row in scan_rows:
        inference = InferenceJob(**(ddb_service.deserialize(row)))
        if username:
            if check_user_permissions(inference.owner_group_or_role, user_roles, username):
                results.append(inference.__dict__)
        else:
            results.append(inference.__dict__)

    data = {
        'inferences': results
    }

    return ok(data=data, decimal=True)


# POST /inference-api
def inference_l2(raw_event, context):
    request_id = context.aws_request_id
    if 'task_type' not in raw_event or 'sagemaker_endpoint_name' not in raw_event or 'models' not in raw_event:
        return {
            'status': 400,
            'err': f'task_type, sagemaker_endpoint_name, models should be in the request body'
        }
    task_type = raw_event['task_type']
    ep_name = raw_event['sagemaker_endpoint_name']

    prepare_infer_event = {
        'sagemaker_endpoint_name': raw_event['sagemaker_endpoint_name'],
        'task_type': task_type,
        'models': raw_event['models'],
        'filters': {
            'creator': 'l2api'
        }
    }
    prepare_resp = prepare_inference(prepare_infer_event, context)

    if 'inference' not in prepare_resp or 'api_params_s3_location' not in prepare_resp['inference']:
        return {
            'status': 500,
            'err': f'fail to prepare inference for {request_id}, no s3 location is generated'
        }

    s3_location = prepare_resp['inference']['api_params_s3_location']
    bucket, s3_file_key = split_s3_path(s3_location)

    # merge the parameters with template
    param_template = load_json_from_s3(bucket_name, 'template/inferenceTemplate.json')
    merged_param = {**param_template, **raw_event}
    upload_json_to_s3(bucket_name, s3_file_key, merged_param)

    run_infer_resp = run_inference({
        'pathStringParameters': {
            'inference_id': request_id
        }
    }, context)

    return {
        'status': 200,
        'inference': {
            'inference_id': request_id,
            'status': run_infer_resp['inference']['status'],
            'output_path': run_infer_resp['inference']['output_path'],
            'models': prepare_resp['inference']['models'],
            'api_params_s3_location': s3_location,
            'type': task_type,
            'endpoint_name': ep_name
        }
    }


# fixme: this is a very expensive function
def _get_checkpoint_by_name(ckpt_name, model_type, status='Active') -> CheckPoint:
    if model_type == 'VAE' and ckpt_name in ['None', 'Automatic']:
        return CheckPoint(
            id=model_type,
            checkpoint_names=[ckpt_name],
            s3_location='None',
            checkpoint_type=model_type,
            checkpoint_status=CheckPointStatus.Active,
            timestamp=0,
        )

    checkpoint_raw = ddb_service.client.scan(
        TableName=checkpoint_table,
        FilterExpression='contains(checkpoint_names, :checkpointName) and checkpoint_type=:model_type and checkpoint_status=:checkpoint_status',
        ExpressionAttributeValues={
            ':checkpointName': {'S': ckpt_name},
            ':model_type': {'S': model_type},
            ':checkpoint_status': {'S': status}
        }
    )

    from common.ddb_service.types_ import ScanOutput
    named_ = ScanOutput(**checkpoint_raw)
    if checkpoint_raw is None or len(named_['Items']) == 0:
        return None

    return CheckPoint(**ddb_service.deserialize(named_['Items'][0]))


def get_base_inference_param_s3_key(_type: str, request_id: str) -> str:
    return f'{_type}/infer_v2/{request_id}'


# currently only two scheduling ways: by endpoint name and by user
def _schedule_inference_endpoint(endpoint_name, user_id):
    # fixme: endpoint is not indexed by name, and this is very expensive query
    # fixme: we can either add index for endpoint name or make endpoint as the partition key
    if endpoint_name:
        sagemaker_endpoint_raw = ddb_service.scan(sagemaker_endpoint_table, filters={
            'endpoint_name': endpoint_name
        })[0]
        sagemaker_endpoint_raw = ddb_service.deserialize(sagemaker_endpoint_raw)
        if sagemaker_endpoint_raw is None or len(sagemaker_endpoint_raw) == 0:
            raise Exception(f'sagemaker endpoint with name {endpoint_name} is not found')

        if sagemaker_endpoint_raw['endpoint_status'] != 'InService':
            raise Exception(f'sagemaker endpoint is not ready with status: {sagemaker_endpoint_raw["endpoint_status"]}')
        return EndpointDeploymentJob(**sagemaker_endpoint_raw)
    elif user_id:
        sagemaker_endpoint_raws = ddb_service.scan(sagemaker_endpoint_table, filters=None)
        user_roles = get_user_roles(ddb_service, user_table, user_id)
        available_endpoints = []
        for row in sagemaker_endpoint_raws:
            endpoint = EndpointDeploymentJob(**ddb_service.deserialize(row))
            if endpoint.endpoint_status != 'InService' or endpoint.status == 'deleted':
                continue

            if check_user_permissions(endpoint.owner_group_or_role, user_roles, user_id):
                available_endpoints.append(endpoint)

        if len(available_endpoints) == 0:
            raise Exception(f'no available Endpoints for user "{user_id}"')

        return random.choice(available_endpoints)
