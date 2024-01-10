import dataclasses
import json
import logging
import os
import random
from datetime import datetime
from typing import List, Any, Optional

from common.ddb_service.client import DynamoDbUtilsService
from common.response import bad_request, created
from common.util import generate_presign_url
from libs.data_types import CheckPoint, CheckPointStatus
from libs.data_types import InferenceJob, EndpointDeploymentJob
from libs.utils import get_user_roles, check_user_permissions

bucket_name = os.environ.get('S3_BUCKET')
checkpoint_table = os.environ.get('CHECKPOINT_TABLE')
sagemaker_endpoint_table = os.environ.get('DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME')
inference_table_name = os.environ.get('DDB_INFERENCE_TABLE_NAME')
user_table = os.environ.get('MULTI_USER_TABLE')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)


@dataclasses.dataclass
class PrepareEvent:
    task_type: str
    models: dict[str, List[str]]  # [checkpoint_type: names] this is same as checkpoint if confused
    filters: dict[str, Any]
    sagemaker_endpoint_name: Optional[str] = ""
    user_id: Optional[str] = ""
    inference_type: Optional[str] = None


# POST /inference/v2
def handler(raw_event, context):
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
        inference_endpoint = _schedule_inference_endpoint(event.sagemaker_endpoint_name, event.inference_type,
                                                          event.user_id)
        endpoint_name = inference_endpoint.endpoint_name
        endpoint_id = inference_endpoint.EndpointDeploymentJobId
        instance_type = inference_endpoint.instance_type

        # generate param s3 location for upload
        param_s3_key = f'{get_base_inference_param_s3_key(_type, request_id)}/api_param.json'
        s3_location = f's3://{bucket_name}/{param_s3_key}'
        presign_url = generate_presign_url(bucket_name, param_s3_key)
        inference_job = InferenceJob(
            InferenceJobId=request_id,
            startTime=str(datetime.now()),
            status='created',
            taskType=_type,
            inference_type=event.inference_type,
            owner_group_or_role=[event.user_id],
            params={
                'input_body_s3': s3_location,
                'input_body_presign_url': presign_url,
                'sagemaker_inference_endpoint_id': endpoint_id,
                'sagemaker_inference_instance_type': instance_type,
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
        return created(data=resp)
    except Exception as e:
        return bad_request(message=str(e))


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
def _schedule_inference_endpoint(endpoint_name, inference_type, user_id):
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
            if endpoint.endpoint_type != inference_type:
                continue
            if check_user_permissions(endpoint.owner_group_or_role, user_roles, user_id):
                available_endpoints.append(endpoint)

        if len(available_endpoints) == 0:
            raise Exception(f'no available {inference_type} endpoints for user "{user_id}"')

        return random.choice(available_endpoints)
