import dataclasses
import logging
import os
from datetime import datetime
from typing import List, Any

from sagemaker import Predictor
from sagemaker.deserializers import JSONDeserializer
from sagemaker.predictor_async import AsyncPredictor
from sagemaker.serializers import JSONSerializer

from common.ddb_service.client import DynamoDbUtilsService
from common.util import generate_presign_url
from inference_v2._types import InferenceJob, InvocationsRequest
from model_and_train._types import CheckPoint

bucket_name = os.environ.get('S3_BUCKET')
checkpoint_table = os.environ.get('CHECKPOINT_TABLE')
sagemaker_endpoint_table = os.environ.get('DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME')
inference_table_name = os.environ.get('DDB_INFERENCE_TABLE_NAME')

logger = logging.getLogger('inference_v2')
ddb_service = DynamoDbUtilsService(logger=logger)


@dataclasses.dataclass
class PrepareEvent:
    sagemaker_endpoint_name: str
    task_type: str
    models: dict[str, List[str]]  # [checkpoint_type: names] this is same as checkpoint if confused
    filters: dict[str, Any]


# POST /v2/inference
def prepare_inference(raw_event, context):
    request_id = context.aws_request_id
    event = PrepareEvent(**raw_event)
    _type = event.task_type

    if _type not in ['txt2img', 'img2img']:
        return {
            'status': 400,
            'err': f'task type {event.task_type} should be either txt2img or img2img'
        }

    # check if endpoint table for endpoint status and existence
    # fixme: endpoint is not indexed by name, and this is very expensive query
    # fixme: we can either add index for endpoint name or make endpoint as the partition key
    sagemaker_endpoint_raw = ddb_service.scan(sagemaker_endpoint_table, filters={
        'endpoint_name': event.sagemaker_endpoint_name
    })[0]
    sagemaker_endpoint_raw = ddb_service.deserialize(sagemaker_endpoint_raw)
    if sagemaker_endpoint_raw is None or len(sagemaker_endpoint_raw) == 0:
        return {
            'status': 500,
            'error': f'sagemaker endpoint with name {event.sagemaker_endpoint_name} is not found'
        }

    if sagemaker_endpoint_raw['endpoint_status'] != 'InService':
        return {
            'status': 400,
            'error': f'sagemaker endpoint is not ready with status: {sagemaker_endpoint_raw["endpoint_status"]}'
        }

    endpoint_name = sagemaker_endpoint_raw['endpoint_name']
    endpoint_id = sagemaker_endpoint_raw['EndpointDeploymentJobId']

    # check if model(checkpoint) path(s) exists. return error if not
    ckpts = []
    ckpts_to_upload = []
    for ckpt_type, names in event.models.items():
        for name in names:
            ckpt = _get_checkpoint_by_name(name, ckpt_type)
            if ckpt is None:
                ckpts_to_upload.append({
                    'name': name,
                    'ckpt_type': ckpt_type
                })
            else:
                ckpts.append(ckpt)

    if len(ckpts_to_upload) > 0:
        return {
            'status': 400,
            'error': [f'checkpoint with name {c["name"]}, type {c["ckpt_type"]} is not found' for c in ckpts_to_upload]
        }

    # generate param s3 location for upload
    param_s3_key = f'{get_base_inference_param_s3_key(_type, request_id)}/api_param.json'
    s3_location = f's3://{bucket_name}/{param_s3_key}'
    presign_url = generate_presign_url(bucket_name, param_s3_key)

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

    inference_job = InferenceJob(
        InferenceJobId=request_id,
        startTime=str(datetime.now()),
        status='created',
        taskType=_type,
        params={
            'input_body_s3': s3_location,
            'input_body_presign_url': presign_url,
            'used_models': used_models,
            'sagemaker_inference_endpoint_id': endpoint_id,
            'sagemaker_inference_endpoint_name': endpoint_name,
        },
    )
    ddb_service.put_items(inference_table_name, entries=inference_job.__dict__)
    return {
        'status': 200,
        'inference': {
            'id': request_id,
            'type': _type,
            'api_params_s3_location': s3_location,
            'api_params_s3_upload_url': presign_url,
            'models': [{'id': ckpt.id, 'name': ckpt.checkpoint_names, 'type': ckpt.checkpoint_type} for ckpt in ckpts]
        }
    }


# PUT /v2/inference/{inference_id}/run
def run_inference(event, _):
    _filter = {}
    if 'pathStringParameters' not in event:
        return {
            'statusCode': '500',
            'error': 'path parameter /v2/inference/{inference_id}/run are needed'
        }

    infer_id = event['pathStringParameters']['inference_id']
    if not infer_id or len(infer_id) == 0:
        return {
            'statusCode': '500',
            'error': 'path parameter /v2/inference/{inference_id}/run are needed, typically inference id is not found'
        }

    # get the inference job from ddb by job id
    inference_raw = ddb_service.get_item(inference_table_name, {
        'InferenceJobId': infer_id
    })

    assert inference_raw is not None and len(inference_raw) > 0
    inference_job = InferenceJob(**inference_raw)
    endpoint_name = inference_job.params['sagemaker_inference_endpoint_name']
    # payload = inference_job.params
    payload = InvocationsRequest(
        task=inference_job.taskType,
        username="test",
        models={
            "space_free_size": 4e10,
            **inference_job.params['used_models'],
        },
        param_s3=inference_job.params['input_body_s3']
    )

    # start async inference
    predictor = Predictor(endpoint_name)
    initial_args = {"InvocationTimeoutSeconds": 3600}
    predictor = AsyncPredictor(predictor, name=endpoint_name)
    predictor.serializer = JSONSerializer()
    predictor.deserializer = JSONDeserializer()
    prediction = predictor.predict_async(data=payload.__dict__, initial_args=initial_args, inference_id=infer_id)
    output_path = prediction.output_path

    # update the ddb job status to 'inprogress' and save to ddb
    inference_job.status = 'inprogress'
    inference_job.params['output_path'] = output_path
    ddb_service.put_items(inference_table_name, inference_job.__dict__)

    return {
        'status': 200,
        'inference': {
            'inference_id': infer_id,
            'status': inference_job.status,
            'endpoint_name': endpoint_name,
            'output_path': output_path
        }
    }


# fixme: this is a very expensive function
def _get_checkpoint_by_name(ckpt_name, model_type, status='Active') -> CheckPoint:
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
