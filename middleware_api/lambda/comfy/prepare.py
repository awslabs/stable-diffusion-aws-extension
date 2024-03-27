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
from sagemaker import Predictor
from sagemaker.base_deserializers import JSONDeserializer
from sagemaker.base_serializers import JSONSerializer

from client import DynamoDbUtilsService
from libs.comfy_data_types import ComfySyncTable
from libs.data_types import EndpointDeploymentJob
from libs.enums import ComfyEnvPrepareType, ComfyTaskType, ComfySyncStatus
from response import ok

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

region = os.environ.get('AWS_REGION')
bucket_name = os.environ.get('BUCKET_NAME')
sqs_url = os.environ.get('SQS_URL')
inference_monitor_table = os.environ.get('INSTANCE_MONITOR_TABLE')
sync_table = os.environ.get('SYNC_TABLE')
endpoint_table = os.environ.get('ENDPOINT_TABLE')
CONFIG_TABLE = os.environ.get('CONFIG_TABLE')

ddb_service = DynamoDbUtilsService(logger=logger)


@dataclass
class PrepareEnvEvent:
    endpoint_name: str
    need_reboot: bool = False
    prepare_type: Optional[str] = 'default'
    # notice !!! must not be prefixed with "/"
    s3_source_path: Optional[str] = ''
    local_target_path: Optional[str] = ''
    sync_script: Optional[str] = ''


def get_endpoint_info(endpoint_name: str):
    endpoint_raw = ddb_service.scan(endpoint_table, filters={'endpoint_name': endpoint_name})[0]
    endpoint_raw = ddb_service.deserialize(endpoint_raw)
    if endpoint_raw is None or len(endpoint_raw) == 0:
        raise Exception(f'sagemaker endpoint with name {endpoint_name} is not found')

    if endpoint_raw['endpoint_status'] != 'InService':
        raise Exception(f'sagemaker endpoint is not ready with status: {endpoint_raw["endpoint_status"]}')
    return EndpointDeploymentJob(**endpoint_raw)


def rebuild_payload(event):
    payload = event.__dict__
    payload['task_type'] = ComfyTaskType.PREPARE
    payload["bucket_name"] = bucket_name
    payload["sqs_url"] = sqs_url
    payload["prepare_type"] = ComfyEnvPrepareType[event.prepare_type]
    payload["s3_source_path"] = event.s3_source_path
    payload["local_target_path"] = event.local_target_path
    payload["need_reboot"] = event.need_reboot
    payload["sync_script"] = event.sync_script
    return payload


def prepare_sagemaker_env(request_id: str, event: PrepareEnvEvent):
    # payload = {"endpoint_name": "ComfyEndpoint-endpoint", "prepare_type": "all"}
    payload = rebuild_payload(event)
    endpoint_name = event.endpoint_name
    if endpoint_name is None:
        raise Exception(f'endpoint name should not be null')
    endpoint_info = get_endpoint_info(endpoint_name)
    if not endpoint_info:
        raise Exception(f'endpoint not found with name {endpoint_name}')

    sync_job = ComfySyncTable(
        request_id=request_id,
        endpoint_name=event.endpoint_name,
        endpoint_id=endpoint_info.EndpointDeploymentJobId,
        instance_count=endpoint_info.current_instance_count,
        sync_instance_count=0,
        prepare_type=event.prepare_type,
        need_reboot=event.need_reboot,
        s3_source_path=event.s3_source_path,
        local_target_path=event.local_target_path,
        sync_script=event.sync_script,
        endpoint_snapshot=json.dumps(endpoint_info),
        sync_status=ComfySyncStatus.INIT,
        request_time=datetime.now(),
    )
    save_sync_ddb_resp = ddb_service.put_items(sync_table, entries=sync_job.__dict__)
    logger.info(str(save_sync_ddb_resp))

    # TODO endpoint上实时写入ComfyInstanceMonitorTable

    # TODO 异步查询sync表的实例数 获取最新状态

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
