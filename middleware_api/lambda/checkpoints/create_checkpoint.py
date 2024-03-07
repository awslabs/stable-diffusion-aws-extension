import datetime
import json
import logging
import os
import urllib.parse
from dataclasses import dataclass
from typing import Any

import boto3
import requests

from common.const import PERMISSION_CHECKPOINT_ALL, PERMISSION_CHECKPOINT_CREATE
from common.ddb_service.client import DynamoDbUtilsService
from common.response import bad_request, created, accepted
from libs.common_tools import get_base_checkpoint_s3_key, \
    batch_get_s3_multipart_signed_urls
from libs.data_types import CheckPoint, CheckPointStatus, MultipartFileReq
from libs.utils import get_user_roles, permissions_check, response_error

checkpoint_table = os.environ.get('CHECKPOINT_TABLE')
bucket_name = os.environ.get('S3_BUCKET')
checkpoint_type = ["Stable-diffusion", "embeddings", "Lora", "hypernetworks", "ControlNet", "VAE"]
user_table = os.environ.get('MULTI_USER_TABLE')
upload_by_url_lambda_name = os.environ.get('UPLOAD_BY_URL_LAMBDA_NAME')
CN_MODEL_EXTS = [".pt", ".pth", ".ckpt", ".safetensors", ".yaml"]

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)
MAX_WORKERS = 10

lambda_client = boto3.client('lambda')


@dataclass
class CreateCheckPointEvent:
    checkpoint_type: str
    params: dict[str, Any]
    filenames: [MultipartFileReq] = None
    urls: [str] = None


def handler(raw_event, context):
    try:
        logger.info(json.dumps(raw_event))
        request_id = context.aws_request_id
        event = CreateCheckPointEvent(**json.loads(raw_event['body']))

        username = permissions_check(raw_event, [PERMISSION_CHECKPOINT_ALL, PERMISSION_CHECKPOINT_CREATE])

        # all urls or filenames must be passed check
        check_filenames_unique(event)

        if event.urls:
            return invoke_url_lambda(event)

        _type = event.checkpoint_type

        base_key = get_base_checkpoint_s3_key(_type, 'custom', request_id)
        presign_url_map = batch_get_s3_multipart_signed_urls(
            bucket_name=bucket_name,
            base_key=base_key,
            filenames=event.filenames
        )

        checkpoint_params = {}
        if event.params is not None and len(event.params) > 0:
            checkpoint_params = event.params

        checkpoint_params['created'] = str(datetime.datetime.now())
        checkpoint_params['multipart_upload'] = {}
        multiparts_resp = {}
        for key, val in presign_url_map.items():
            checkpoint_params['multipart_upload'][key] = {
                'upload_id': val['upload_id'],
                'bucket': val['bucket'],
                'key': val['key'],
            }
            multiparts_resp[key] = val['s3_signed_urls']

        filenames_only = []
        for f in event.filenames:
            file = MultipartFileReq(**f)
            filenames_only.append(file.filename)

        if len(filenames_only) == 0:
            return bad_request(message='no checkpoint name (file names) detected')

        user_roles = ['*']
        if username:
            checkpoint_params['creator'] = username
            user_roles = get_user_roles(ddb_service, user_table, username)

        checkpoint = CheckPoint(
            id=request_id,
            checkpoint_type=_type,
            s3_location=f's3://{bucket_name}/{base_key}',
            checkpoint_names=filenames_only,
            checkpoint_status=CheckPointStatus.Initial,
            params=checkpoint_params,
            timestamp=datetime.datetime.now().timestamp(),
            allowed_roles_or_users=user_roles
        )
        ddb_service.put_items(table=checkpoint_table, entries=checkpoint.__dict__)
        data = {
            'checkpoint': {
                'id': request_id,
                'type': _type,
                's3_location': checkpoint.s3_location,
                'status': checkpoint.checkpoint_status.value,
                'params': checkpoint.params
            },
            's3PresignUrl': multiparts_resp
        }
        return created(data=data)
    except Exception as e:
        return response_error(e)


def invoke_url_lambda(event: CreateCheckPointEvent):
    urls = list(set(event.urls))

    for url in urls:
        resp = lambda_client.invoke(
            FunctionName=upload_by_url_lambda_name,
            InvocationType='Event',
            Payload=json.dumps({
                'checkpoint_type': event.checkpoint_type,
                'params': event.params,
                'url': url,
            })
        )
        logger.info(resp)
    return accepted(message='Checkpoint creation in progress, please check later')


def check_filenames_unique(event: CreateCheckPointEvent):
    names = []

    if event.filenames:
        for file in event.filenames:
            names.append(file['filename'])

    if event.urls:
        for url in event.urls:
            url = get_real_url(url)
            filename = get_download_file_name(url)
            names.append(filename)

    logger.info(f"names: {names}")

    check_ckpt_name_unique(names)


def check_ckpt_name_unique(names: [str]):
    if len(names) == 0:
        return

    ckpts = ddb_service.scan(table=checkpoint_table)
    exists_names = []
    for ckpt in ckpts:
        if 'checkpoint_names' not in ckpt:
            continue
        if 'L' not in ckpt['checkpoint_names']:
            continue
        for name in ckpt['checkpoint_names']['L']:
            exists_names.append(name['S'])

    logger.info(json.dumps(exists_names))

    for name in names:
        if name.strip() in exists_names:
            raise Exception(f'{name} already exists, '
                            f'please use another or rename/delete exists')


def get_real_url(url: str):
    url = url.strip()
    if url.startswith('https://civitai.com/api/download/models/'):
        response = requests.get(url, allow_redirects=False)
    else:
        response = requests.head(url, allow_redirects=True, timeout=10)

    if response and response.status_code == 307:
        if response.headers and 'Location' in response.headers:
            return response.headers.get('Location')
    return url


def get_download_file_name(url: str):
    parsed_url = urllib.parse.urlparse(url)
    return os.path.basename(parsed_url.path)
