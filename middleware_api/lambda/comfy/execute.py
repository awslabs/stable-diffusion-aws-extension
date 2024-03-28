import base64
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import boto3
import sagemaker
from aws_lambda_powertools import Tracer
from sagemaker import Predictor
from sagemaker.base_deserializers import JSONDeserializer
from sagemaker.base_serializers import JSONSerializer

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok
from libs.comfy_data_types import ComfyExecuteTable
from libs.enums import ComfyExecuteType
from libs.utils import get_endpoint_by_name, response_error

tracer = Tracer()
region = os.environ.get('AWS_REGION')
bucket_name = os.environ.get('S3_BUCKET_NAME')
execute_table = os.environ.get('EXECUTE_TABLE')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)

index_name = "endpoint_name-startTime-index"


@dataclass
class ExecuteEvent:
    prompt_id: str
    prompt: dict
    endpoint_name: Optional[str] = ''
    inference_type: Optional[str] = None
    need_sync: bool = True
    number: Optional[str] = None
    front: Optional[bool] = None
    extra_data: Optional[dict] = None
    client_id: Optional[str] = None


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
    logger.info(f"endpoint: {ep}")

    # payload = {"number": str(number), "prompt": prompt, "prompt_id": prompt_id, "extra_data": extra_data,
    #            "endpoint_name": "ComfyEndpoint-endpoint", "need_sync": True}
    payload = event.__dict__
    logger.info('inference payload: {}'.format(payload))
    # TODO 同步异步推理的选择 以及endpoint的选择
    session = boto3.Session(region_name=region)
    sagemaker_session = sagemaker.Session(boto_session=session)
    predictor = Predictor(endpoint_name=endpoint_name, sagemaker_session=sagemaker_session)
    inference_id = str(uuid.uuid4())
    predictor.serializer = JSONSerializer()
    predictor.deserializer = JSONDeserializer()
    logger.info("Start predict to get response:")
    start = time.time()
    prediction = predictor.predict(data=payload, inference_id=inference_id)
    logger.info(f"Response object: {prediction}")
    r = prediction
    logger.info(r)
    # TODO 获取哪些可用的endpoint name 以及instance type 默认异步
    inference_job = ComfyExecuteTable(
        prompt_id=event.prompt_id,
        endpoint_name=event.endpoint_name,
        inference_type=event.inference_type,
        # TODO shell脚本补全instanceId 补全id 知道推理环境
        instance_id='',
        need_sync=event.need_sync,
        status=ComfyExecuteType.CREATED,
        # prompt: str number: Optional[int] front: Optional[str] extra_data: Optional[str] client_id: Optional[str]
        prompt_params={'prompt': event.prompt, 'number': event.number, 'front': event.front,
                       'extra_data': event.extra_data, 'client_id': event.client_id},
        # 带后期再看是否要将参数统一变成s3的文件来管理 此处为入参路径 优先级不高 一期先放
        prompt_path='',
        create_time=datetime.now(),
        start_time=datetime.now(),
        complete_time=None,
        output_path='',
        output_files=None
    )

    save_ddb_resp = ddb_service.put_items(execute_table, entries=inference_job.__dict__)
    logger.info(f"Time taken: {time.time() - start}s save msg: {save_ddb_resp}")


@tracer.capture_lambda_handler
def handler(raw_event, ctx):
    try:
        logger.info(f"execute start... Received event: {raw_event}")
        logger.info(f"Received ctx: {ctx}")
        event = ExecuteEvent(**json.loads(raw_event['body']))
        invoke_sagemaker_inference(event)
        # sync_param = build_s3_images_request(event.prompt_id, bucket_name, f'output/{event.prompt_id}')
        # logger.info('sync_param : {}'.format(sync_param))
        # response = requests.post(event.callback_url, json=sync_param)
        # logger.info(f'call back url :{event.callback_url}, json:{json}, response:{response}')
        # logger.info("execute end...")
        return ok(data=event.prompt_id)
    except Exception as e:
        return response_error(e)
