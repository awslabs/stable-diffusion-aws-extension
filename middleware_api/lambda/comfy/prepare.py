import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from typing import Optional

import boto3
import sagemaker
from sagemaker import Predictor
from sagemaker.base_deserializers import JSONDeserializer
from sagemaker.base_serializers import JSONSerializer

from libs.enums import ComfyEnvPrepareType, ComfyTaskType
from response import ok

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

region = os.environ.get('AWS_REGION')
bucket_name = os.environ.get('BUCKET_NAME')
sqs_url = os.environ.get('SQS_URL')


@dataclass
class PrepareEnvEvent:
    endpoint_name: str
    need_reboot: bool = False
    prepare_type: Optional[str] = 'default'
    # notice !!! must not be prefixed with "/"
    s3_source_path: Optional[str] = ''
    local_target_path: Optional[str] = ''


def prepare_sagemaker_env(request_id: str, event: PrepareEnvEvent):

    # payload = {"endpoint_name": "ComfyEndpoint-endpoint", "prepare_type": "all"}
    payload = event.__dict__
    payload['task_type'] = ComfyTaskType.PREPARE

    payload["bucket_name"] = bucket_name
    payload["sqs_url"] = sqs_url
    payload["region"] = region

    payload["prepare_type"] = ComfyEnvPrepareType[event.prepare_type]
    payload["s3_source_path"] = event.s3_source_path
    payload["local_target_path"] = event.local_target_path

    # TODO
    payload["need_reboot"] = event.need_reboot
    endpoint_name = event.endpoint_name

    # TODO 根据 endpoint_name 获取所有实例列表
    # TODO 逐一调用实例列表执行初始化接口-这个时间较长 可以按照异步调用 等待初始化结果

    session = boto3.Session(region_name=region)
    sagemaker_session = sagemaker.Session(boto_session=session)
    predictor = Predictor(endpoint_name=endpoint_name, sagemaker_session=sagemaker_session)
    inference_id = str(uuid.uuid4())
    predictor.serializer = JSONSerializer()
    predictor.deserializer = JSONDeserializer()
    logger.info("Start to prepare environment and to get response")
    start = time.time()
    prediction = predictor.predict(data=payload, inference_id=inference_id)
    logger.info(f"Response object: {prediction}")
    r = prediction
    logger.info(r)
    logger.info(f"Time taken: {time.time() - start}s")


def handler(raw_event, ctx):
    logger.info(f"prepare env start... Received event: {raw_event}")
    logger.info(f"Received ctx: {ctx}")
    request_id = ctx.aws_request_id

    event = PrepareEnvEvent(**json.loads(raw_event['body']))
    prepare_sagemaker_env(request_id, event)
    return ok(data=event.endpoint_name)
