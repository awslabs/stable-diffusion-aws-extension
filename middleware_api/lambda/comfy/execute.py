import base64
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass

import boto3
import sagemaker
from sagemaker import Predictor
from sagemaker.base_deserializers import JSONDeserializer
from sagemaker.base_serializers import JSONSerializer

from response import ok

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

region = os.environ.get('AWS_REGION')
bucket_name = os.environ.get('BUCKET_NAME')
sqs_url = os.environ.get('SQS_URL')


@dataclass
class ExecuteEvent:
    prompt_id: str
    prompt: dict
    endpoint_name: str
    need_sync: bool = True
    need_prepare: bool = True
    number: str = None
    front: bool = None
    extra_data: dict = None
    client_id: str = None
    callback_url: str = None


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


def invoke_sagemaker_inference(event: ExecuteEvent):
    endpoint_name = event.endpoint_name
    # payload = {"number": str(number), "prompt": prompt, "prompt_id": prompt_id, "extra_data": extra_data,
    #            "endpoint_name": "ComfyEndpoint-endpoint", "need_prepare": True, "need_sync": True}
    payload = event.__dict__
    # if payload['need_prepare']:
    payload["bucket_name"] = bucket_name
    payload["sqs_url"] = sqs_url
    payload["region"] = region

    logger.info('payload: {}'.format(payload))
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
    logger.info(f"Time taken: {time.time() - start}s")


def handler(raw_event, ctx):
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
