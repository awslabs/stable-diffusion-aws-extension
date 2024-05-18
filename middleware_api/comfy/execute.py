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
from common.util import s3_scan_files, generate_presigned_url_for_keys, \
    record_latency_metrics, record_count_metrics, get_workflow_name
from libs.comfy_data_types import ComfyExecuteTable, InferenceResult
from libs.enums import ComfyExecuteType, EndpointStatus, ServiceType
from libs.utils import get_endpoint_by_name, response_error

tracer = Tracer()
region = os.environ.get('AWS_REGION')
bucket_name = os.environ.get('S3_BUCKET_NAME')
execute_table = os.environ.get('EXECUTE_TABLE')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)
endpoint_instance_id = os.environ.get('ENDPOINT_INSTANCE_ID')
ddb_service = DynamoDbUtilsService(logger=logger)

sqs_url = os.environ.get('MERGE_SQS_URL')

index_name = "endpoint_name-startTime-index"
predictors = {}

multi_gpu_instance_type_list = ['ml.p5.48xlarge', 'ml.p4d.24xlarge', 'ml.p3.8xlarge', 'ml.p3.16xlarge',
                                'ml.p3dn.24xlarge', 'ml.p2.8xlarge', 'ml.p2.16xlarge', 'ml.g4dn.12xlarge',
                                'ml.g5.12xlarge', 'ml.g5.24xlarge', 'ml.g5.48xlarge']


@dataclass
class PrepareProps:
    need_reboot: Optional[bool] = False
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
    workflow: Optional[str] = None
    need_prepare: Optional[bool] = False
    prepare_props: Optional[PrepareProps] = None
    multi_async: Optional[bool] = False


def sen_sqs_msg(message_body, endpoint_name):
    sqs_client = boto3.client('sqs', region_name=region)
    response = sqs_client.send_message(
        QueueUrl=sqs_url,
        MessageBody=json.dumps(message_body),
        MessageGroupId=endpoint_name
    )
    message_id = response['MessageId']
    return message_id


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

    if ep.endpoint_status not in [EndpointStatus.IN_SERVICE.value, EndpointStatus.UPDATING.value]:
        raise Exception(f"Endpoint {endpoint_name} is {ep.endpoint_status} status, not InService or Updating.")

    if event.workflow:
        event.workflow = get_workflow_name(event.workflow, ep.instance_type)

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
        prompt_params={'prompt': str(event.prompt),
                       'number': event.number,
                       'front': event.front,
                       'extra_data': str(event.extra_data),
                       'client_id': event.client_id},
        prompt_path='',
        create_time=datetime.now().isoformat(),
        sagemaker_raw={},
        output_path='',
        temp_path='',
        output_files=[],
        temp_files=[],
        multi_async=event.multi_async,
        batch_id='',
        workflow=event.workflow,
    )

    logger.info(f"inference job: {inference_job.__dict__}")

    record_count_metrics(ep_name=ep.endpoint_name,
                         metric_name='InferenceTotal',
                         service=ServiceType.Comfy.value,
                         workflow=inference_job.workflow
                         )

    if event.multi_async and ep.endpoint_type == 'Async' and ep.instance_type in multi_gpu_instance_type_list:
        logger.info(f"executing multi-gpu inference {ep.instance_type} {ep.endpoint_type} {event.multi_async}")
        save_item = inference_job.__dict__
        ddb_service.put_items(execute_table, entries=save_item)
        sen_sqs_msg({"event": payload, "save_item": save_item, "inference_id": inference_id}, endpoint_name)

        # just for test multi gpu
        # payload1 = payload
        # payload1['prompt_id'] = payload['prompt_id']+"1"
        # save_item1 = save_item
        # save_item1['prompt_id'] = payload['prompt_id']+"1"
        # sen_sqs_msg({"event": payload1, "save_item": save_item1, "inference_id": inference_id+"1"}, endpoint_name)
        # payload2 = payload
        # payload2['prompt_id'] = payload['prompt_id'] + "1"
        # save_item2 = save_item
        # save_item2['prompt_id'] = payload['prompt_id'] + "1"
        # sen_sqs_msg({"event": payload2, "save_item": save_item2, "inference_id": inference_id+"2"}, endpoint_name)

        return created(data=response_schema(inference_job), decimal=True)

    elif ep.endpoint_type == 'Async':
        ddb_service.put_items(execute_table, entries=inference_job.__dict__)
        resp = async_inference([payload], inference_id, ep.endpoint_name)
        # TODO status check and save
        logger.info(f"async inference {ep.instance_type} {ep.endpoint_type} {event.multi_async} response: {resp}")
        return created(data=response_schema(inference_job), decimal=True)

    inference_job.start_time = datetime.now().isoformat()
    ddb_service.put_items(execute_table, entries=inference_job.__dict__)

    resp = real_time_inference([payload], inference_id, ep.endpoint_name)

    logger.info(f"real time inference response: {resp}")
    if resp and len(resp) > 0:
        resp = InferenceResult(**resp[0])
        resp = s3_scan_files(resp)

        inference_job.status = resp.status
        inference_job.sagemaker_raw = resp.__dict__
        inference_job.output_path = resp.output_path
        inference_job.output_files = resp.output_files
        inference_job.temp_path = resp.temp_path
        inference_job.temp_files = resp.temp_files
        inference_job.complete_time = datetime.now().isoformat()
        if resp.status == 'fail' or resp.status != 'Completed' or resp.status != 'success':
            inference_job.message = resp.message

        ddb_service.put_items(execute_table, entries=inference_job.__dict__)

        if ep.endpoint_type == 'Real-time':
            inference_job.output_files = generate_presigned_url_for_keys(inference_job.output_path,
                                                                         inference_job.output_files)
            inference_job.temp_files = generate_presigned_url_for_keys(inference_job.temp_path,
                                                                       inference_job.temp_files)

        if resp.status == 'fail' or resp.status != 'Completed' or resp.status != 'success':
            inference_job.message = resp.message
            record_count_metrics(ep_name=ep.endpoint_name,
                                 metric_name='InferenceFailed',
                                 service=ServiceType.Comfy.value,
                                 workflow=inference_job.workflow
                                 )
        else:
            record_count_metrics(ep_name=ep.endpoint_name,
                                 metric_name='InferenceSucceed',
                                 service=ServiceType.Comfy.value,
                                 workflow=inference_job.workflow
                                 )
            record_latency_metrics(start_time=inference_job.start_time,
                                   ep_name=ep.endpoint_name,
                                   metric_name='InferenceLatency',
                                   workflow=inference_job.workflow,
                                   service=ServiceType.Comfy.value)
    else:
        logger.info(f"inference error by sg resp none!{resp}")
        record_count_metrics(ep_name=ep.endpoint_name,
                             metric_name='InferenceFailed',
                             service=ServiceType.Comfy.value,
                             workflow=inference_job.workflow
                             )
    return ok(data=response_schema(inference_job), decimal=True)


def response_schema(inference_job: ComfyExecuteTable):
    if not inference_job.output_files:
        inference_job.output_files = []

    if not inference_job.temp_files:
        inference_job.temp_files = []

    data = {
        'prompt_id': inference_job.prompt_id,
        'status': inference_job.status,
        'create_time': inference_job.create_time,
        'endpoint_name': inference_job.endpoint_name,
        'inference_type': inference_job.inference_type,
        'need_sync': inference_job.need_sync,
        'start_time': inference_job.start_time,
        'complete_time': inference_job.complete_time,
        'output_path': inference_job.output_path,
        'output_files': inference_job.output_files,
        'temp_path': inference_job.temp_path,
        'temp_files': inference_job.temp_files,
    }

    return data


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
