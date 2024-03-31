import base64
import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import boto3
from aws_lambda_powertools import Tracer
from sagemaker import Predictor
from sagemaker.deserializers import JSONDeserializer
from sagemaker.predictor_async import AsyncPredictor
from sagemaker.serializers import JSONSerializer

from common.ddb_service.client import DynamoDbUtilsService
from common.excepts import BadRequestException
from common.response import ok, created
from common.util import s3_scan_files
from libs.comfy_data_types import ComfyExecuteTable, InferenceResult
from libs.enums import ComfyExecuteType
from libs.utils import get_endpoint_by_name, response_error

tracer = Tracer()
region = os.environ.get('AWS_REGION')
bucket_name = os.environ.get('S3_BUCKET_NAME')
execute_table = os.environ.get('EXECUTE_TABLE')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)
endpoint_instance_id = os.environ.get('ENDPOINT_INSTANCE_ID')
ddb_service = DynamoDbUtilsService(logger=logger)

index_name = "endpoint_name-startTime-index"
predictors = {}


@dataclass
class PrepareProps:
    prepare_type: Optional[str] = "inputs"
    s3_source_path: Optional[str] = None
    local_target_path: Optional[str] = None
    sync_script: Optional[str] = None


@dataclass
class ExecuteEvent:
    prompt_id: str
    prompt: dict
    endpoint_name: Optional[str] = ''
    need_sync: bool = True
    number: Optional[str] = None
    front: Optional[bool] = None
    extra_data: Optional[dict] = None
    client_id: Optional[str] = None
    need_prepare: bool = False
    prepare_props: Optional[PrepareProps] = None


def build_s3_images_request(prompt_id, bucket_name, s3_path):
    s3 = boto3.client('s3', region_name=region)
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=s3_path)
    image_video_dict = {}
    for obj in response.get('Contents', []):
        object_key = obj['Key']
        file_name = object_key.split('/')[-1]
        if object_key.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.mp4', '.mov', '.avi')):
            response_data = s3.get_object(Bucket=bucket_name, Key=object_key)
            object_data = response_data['Body'].read()
            encoded_data = base64.b64encode(object_data).decode('utf-8')
            image_video_dict[file_name] = encoded_data

    return {'prompt_id': prompt_id, 'image_video_data': image_video_dict}


@tracer.capture_method
def invoke_sagemaker_inference(event: ExecuteEvent):
    endpoint_name = event.endpoint_name

    ep = get_endpoint_by_name(endpoint_name)

    if ep.endpoint_status != 'InService':
        raise Exception(f"Endpoint {endpoint_name} is {ep.endpoint_status} status, not InService.")

    logger.info(f"endpoint: {ep}")

    payload = event.__dict__
    logger.info('inference payload: {}'.format(payload))

    inference_id = str(uuid.uuid4())

    job_status = ComfyExecuteType.CREATED.value

    inference_job = ComfyExecuteTable(
        prompt_id=event.prompt_id,
        endpoint_name=event.endpoint_name,
        inference_type=ep.endpoint_type,
        instance_id=endpoint_instance_id,
        need_sync=event.need_sync,
        status=job_status,
        prompt_params={'prompt': event.prompt,
                       'number': event.number,
                       'front': event.front,
                       'extra_data': event.extra_data,
                       'client_id': event.client_id},
        prompt_path='',
        create_time=datetime.now().isoformat(),
        start_time=datetime.now().isoformat(),
        sagemaker_raw={},
        output_path='',
    )

    if ep.endpoint_type == 'Async':
        resp = async_inference(payload, inference_id, ep.endpoint_name)
        logger.info(f"async inference response: {resp}")
        ddb_service.put_items(execute_table, entries=inference_job.__dict__)
        return created(data=inference_job.__dict__)

    # resp = real_time_inference(payload, inference_id, ep.endpoint_name)
    resp = {
        "prompt_id": '11111111-1111-1111',
        "instance_id": 'esd-real-time-test-rgihbd',
        "status": 'success',
        "output_path": f's3://{bucket_name}/images/',
        "temp_path": f's3://{bucket_name}/images/'
    }

    logger.info(f"real time inference response: ")
    logger.info(resp)
    resp = InferenceResult(**resp)
    resp = s3_scan_files(resp)

    inference_job.status = resp.status
    inference_job.sagemaker_raw = resp.__dict__
    inference_job.output_path = resp.output_path
    inference_job.output_files = resp.output_files
    inference_job.temp_path = resp.temp_path
    inference_job.temp_files = resp.temp_files
    inference_job.complete_time = datetime.now().isoformat()

    ddb_service.put_items(execute_table, entries=inference_job.__dict__)

    return ok(data=inference_job.__dict__)


@tracer.capture_lambda_handler
def handler(raw_event, ctx):
    try:
        logger.info(f"execute start... Received event: {raw_event}")
        logger.info(f"Received ctx: {ctx}")
        event = ExecuteEvent(**json.loads(raw_event['body']))

        if not event.prompt:
            raise BadRequestException("Prompt is required")

        return invoke_sagemaker_inference(event)

    except Exception as e:
        return response_error(e)


@tracer.capture_method
def async_inference(payload: any, inference_id, endpoint_name):
    tracer.put_annotation(key="inference_id", value=inference_id)
    initial_args = {"InvocationTimeoutSeconds": 3600}
    return get_async_predict_client(endpoint_name).predict_async(data=payload,
                                                                 initial_args=initial_args,
                                                                 inference_id=inference_id)


@tracer.capture_method
def real_time_inference(data: any, inference_id, endpoint_name):
    tracer.put_annotation(key="inference_id", value=inference_id)
    return get_real_time_predict_client(endpoint_name).predict(data=data, inference_id=inference_id)


@tracer.capture_method
def get_real_time_predict_client(endpoint_name):
    tracer.put_annotation(key="endpoint_name", value=endpoint_name)
    if endpoint_name in predictors:
        return predictors[endpoint_name]

    predictor = Predictor(endpoint_name)
    predictor.serializer = JSONSerializer()
    predictor.deserializer = JSONDeserializer()

    predictors[endpoint_name] = predictor

    return predictor


@tracer.capture_method
def get_async_predict_client(endpoint_name):
    tracer.put_annotation(key="endpoint_name", value=endpoint_name)
    if endpoint_name in predictors:
        return predictors[endpoint_name]

    predictor = Predictor(endpoint_name)
    predictor = AsyncPredictor(predictor, name=endpoint_name)
    predictor.serializer = JSONSerializer()
    predictor.deserializer = JSONDeserializer()

    predictors[endpoint_name] = predictor

    return predictor
