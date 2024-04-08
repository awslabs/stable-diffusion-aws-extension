import decimal
import io
import json
import logging
import math
import os
import subprocess
import sys
import tarfile

import requests

import config as config
from utils.api import Api
from utils.enums import InferenceStatus

logger = logging.getLogger(__name__)


def get_parts_number(local_path: str):
    file_size = os.stat(local_path).st_size
    part_size = 1000 * 1024 * 1024
    return math.ceil(file_size / part_size)


def wget_file(local_file: str, url: str, gcr_url: str = None):
    # if gcr_url is not None and config.is_gcr:
    #     url = gcr_url
    if not os.path.exists(local_file):
        local_path = os.path.dirname(local_file)
        logger.info(f"Downloading {url}")
        wget_process = subprocess.run(['wget', '-qP', local_path, url], capture_output=True)
        if wget_process.returncode != 0:
            raise subprocess.CalledProcessError(wget_process.returncode, 'wget failed')


def create_tar(json_string: str, path: str):
    with io.BytesIO() as tar_buffer:
        with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
            json_bytes = json_string.encode("utf-8")
            json_buffer = io.BytesIO(json_bytes)
            tarinfo = tarfile.TarInfo(name=path)
            tarinfo.size = len(json_bytes)
            tar.addfile(tarinfo, json_buffer)
            return tar_buffer.getvalue()


def list_endpoints(api_instance):
    headers = {
        "x-api-key": config.api_key,
        "username": config.username
    }
    resp = api_instance.list_endpoints(headers=headers)
    assert resp.status_code == 200, resp.dumps()
    endpoints = resp.json()['data']["endpoints"]
    return endpoints


def get_endpoint_status(api_instance, endpoint_name: str):
    endpoints = list_endpoints(api_instance)
    for endpoint in endpoints:
        if endpoint['endpoint_name'] == endpoint_name:
            return endpoint['endpoint_status']
    return None


def get_inference_job_status(api_instance, job_id):
    headers = {
        "x-api-key": config.api_key,
        "username": config.username
    }

    resp = api_instance.get_inference_job(job_id=job_id, headers=headers)

    if InferenceStatus.FAILED.value == resp.json()['data']['status']:
        logger.error(f"Failed inference: {resp.json()['data']}")

    return resp.json()['data']['status']


def get_inference_job_image(api_instance, job_id: str, target_file: str):
    resp = api_instance.get_inference_job(
        job_id=job_id,
        headers={
            "x-api-key": config.api_key,
            "username": config.username
        },
    )

    if 'img_presigned_urls' not in resp.json()['data']:
        raise Exception(f"img_presigned_urls not found in inference job: {resp.json()}")

    if config.compare_content == 'false':
        logger.info(f"compare_content is false, skip comparing image {target_file}")
        return

    img_presigned_urls = resp.json()['data']['img_presigned_urls']

    for img_url in img_presigned_urls:
        resp = requests.get(img_url)

        if not os.path.exists(target_file):
            with open(f"{target_file}", "wb") as f:
                f.write(resp.content)
            raise Exception(f"Image {target_file} first generated")

        if resp.content == open(target_file, "rb").read():
            logger.info(f"Image same with {target_file}")
            return

        # write image to file
        with open(f"{target_file}.png", "wb") as f:
            f.write(resp.content)

        raise Exception(f"Image {target_file} not same with {target_file}.png")

    raise Exception(f"Image not found in inference job: {resp.json()}")


def delete_sagemaker_endpoint(api_instance, endpoint_name: str):
    headers = {
        "x-api-key": config.api_key,
        "username": config.username
    }

    data = {
        "endpoint_name_list": [
            endpoint_name,
        ],
        "username": config.username
    }

    resp = api_instance.delete_endpoints(headers=headers, data=data)
    assert resp.status_code == 204, resp.dumps()


def delete_inference_jobs(inference_id_list: [str]):
    api = Api(config)

    data = {
        "inference_id_list": inference_id_list,
    }

    api.delete_inferences(data=data, headers={"x-api-key": config.api_key, })


def upload_with_put(s3_url, local_file):
    with open(local_file, 'rb') as data:
        response = requests.put(s3_url, data=data)
        response.raise_for_status()


def upload_multipart_file(signed_urls, local_path):
    print(f"uploading {local_path}")
    with open(local_path, "rb") as f:
        parts = []

        for i, signed_url in enumerate(signed_urls):
            part_size = 1000 * 1024 * 1024
            file_data = f.read(part_size)
            response = requests.put(signed_url, data=file_data)
            response.raise_for_status()
            etag = response.headers['ETag']
            parts.append({
                'ETag': etag,
                'PartNumber': i + 1
            })
            print(f'model upload part {i + 1}: {response}')

        return parts


# s_tmax: Infinity
def parse_constant(c: str) -> float:
    if c == "NaN":
        raise ValueError("NaN is not valid JSON")

    if c == 'Infinity':
        return sys.float_info.max

    return float(c)


def update_oas(api_instance: Api):
    headers = {'x-api-key': config.api_key}
    resp = api_instance.doc(headers)
    assert resp.status_code == 200, resp.dumps()

    api_instance.schema = resp.json()

    with open('oas.json', 'w') as f:
        f.write(json.dumps(resp.json(), indent=4))


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        # if passed in an object is instance of Decimal
        # convert it to a string
        if isinstance(obj, decimal.Decimal):
            return str(obj)

        # ️ otherwise use the default behavior
        return json.JSONEncoder.default(self, obj)
