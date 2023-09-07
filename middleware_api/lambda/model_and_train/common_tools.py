import json
import decimal
from typing import Dict, Any

import boto3
import os
from datetime import datetime
from datetime import timedelta
import logging
import concurrent.futures
import urllib.request
import math
import threading

from _types import MultipartFileReq, CheckPoint

PART_SIZE=500 * 1024 * 1024

def batch_get_s3_multipart_signed_urls(bucket_name, base_key, filenames: [MultipartFileReq]) -> Dict[str, Any]:
    presign_url_map = {}
    for f in filenames:
        file = MultipartFileReq(**f)
        key = f'{base_key}/{file.filename}'
        signed_urls = get_s3_multipart_signed_urls(bucket_name, key, parts_number=file.parts_number)
        presign_url_map[file.filename] = signed_urls

    return presign_url_map


def get_s3_multipart_signed_urls(bucket_name, key, parts_number) -> Any:
    s3 = boto3.client('s3')
    response = s3.create_multipart_upload(
        Bucket=bucket_name,
        Key=key,
        Expires=datetime.now() + timedelta(seconds=3600 * 24 * 7)
    )

    upload_id = response['UploadId']

    presign_urls = []

    for i in range(1, parts_number+1):
        presign_url = s3.generate_presigned_url(
            ClientMethod='upload_part',
            Params={
                'Bucket': bucket_name,
                'Key': key,
                'UploadId': upload_id,
                'PartNumber': i
            }
        )
        presign_urls.append(presign_url)
    return {
        's3_signed_urls': presign_urls,
        'upload_id': upload_id,
        'bucket': bucket_name,
        'key': key,
    }


def get_base_model_s3_key(_type: str, name: str, request_id: str) -> str:
    return f'{_type}/model/{name}/{request_id}'


def get_base_checkpoint_s3_key(_type: str, name: str, request_id: str) -> str:
    return f'{_type}/checkpoint/{name}/{request_id}'


def complete_multipart_upload(ckpt: CheckPoint, filename_etag):
    s3 = boto3.client('s3')
    if 'multipart_upload' in ckpt.params:
        multipart = ckpt.params['multipart_upload']
        for filename, val in multipart.items():
            # todo: can add s3 MD5 check here to see if file is upload properly
            if filename in filename_etag:
                filename_etag[filename].sort(key=lambda x: x['PartNumber'])
                response = s3.complete_multipart_upload(
                    Bucket=val['bucket'],
                    Key=val['key'],
                    MultipartUpload={'Parts': filename_etag[filename]},
                    UploadId=val['upload_id']
                )
                print(f'complete upload multipart response {response}')
                response = s3.abort_multipart_upload(
                    Bucket=val['bucket'],
                    Key=val['key'],
                    UploadId=val['upload_id']
                )
                print(f'abort upload multipart response {response}')


def split_s3_path(s3_path):
    path_parts = s3_path.replace("s3://", "").split("/")
    bucket = path_parts.pop(0)
    key = "/".join(path_parts)
    return bucket, key


def upload_part_file(s3, bucket, key, part_number, upload_id, part_data):
    try:
        response = s3.upload_part(
            Bucket=bucket,
            Key=key,
            PartNumber=part_number,
            UploadId=upload_id,
            Body=part_data
        )
        return {'PartNumber': part_number, 'ETag': response['ETag']}
    except Exception as e:
        logging.error(f"Upload of part {part_number} failed: {str(e)}")
        return {'PartNumber': part_number, 'ETag': None}


# Args:
#     url (str): model source file url,eg:eg：https://civitai.com/api/download/models/xxxx or https://huggingface.co/stabilityai/stable-diffusion-xxxx/resolve/main/xxxx.safetensors
#     bucket_name(str): bucket name
#     s3_key(str):s3 key
# Returns:
#     upload_id: s3 uploadId
#     key:s3 key
#     bucket: bucket name
def multipart_upload_from_url(url, bucket_name, s3_key):
    s3 = boto3.client('s3')
    logging.info(f"start multipart_upload_from_url:{url}, {s3_key}")
    lock = threading.Lock()
    try:
        with urllib.request.urlopen(url) as response:
            # 获取文件总大小
            total_size = int(response.info().get('Content-Length'))
            part_count = math.ceil(total_size / PART_SIZE)
            upload_id = s3.create_multipart_upload(Bucket=bucket_name, Key=s3_key,
            Expires=datetime.now() + timedelta(seconds=3600 * 24 * 7))['UploadId']
            logging.info(f"multipart_upload_from_url:   total_size:{total_size}, part_count:{part_count} upload_id:{upload_id}")
            parts = []
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = []
                for part_number in range(1, part_count + 1):
                    with lock:
                        start = (part_number - 1) * PART_SIZE
                        end = min(part_number * PART_SIZE, total_size)
                        part_data = response.read(end - start)
                        futures.append(
                            executor.submit(upload_part_file, s3, bucket_name, s3_key, part_number, upload_id, part_data))

                for future in concurrent.futures.as_completed(futures):
                    parts.append(future.result())
            parts.sort(key=lambda part: part['PartNumber'])
            # 完成Multipart上传
            s3.complete_multipart_upload(
                Bucket=bucket_name,
                Key=s3_key,
                UploadId=upload_id,
                MultipartUpload={'Parts': parts}
            )
            logging.info("Multipart upload completed!")
            return {
                "uploadId": upload_id,
                "key": s3_key,
                "bucket": bucket_name,
            }
    except Exception as e:
        logging.error(f"Multipart upload failed: {str(e)}")
        return None


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        # if passed in object is instance of Decimal
        # convert it to a string
        if isinstance(obj, decimal.Decimal):
            return str(obj)

        #️ otherwise use the default behavior
        return json.JSONEncoder.default(self, obj)

