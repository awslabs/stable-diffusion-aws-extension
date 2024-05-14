import base64
import decimal
import io
import json
import logging
import math
import os
import subprocess
import sys
import tarfile
import time
import uuid
from datetime import datetime, timedelta

import boto3
import requests
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

import config as config
from utils.api import Api
from utils.enums import InferenceStatus, InferenceType

logger = logging.getLogger(__name__)

s3 = boto3.client('s3')


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
        logger.info(f"Downloaded {url}")
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


def get_inference_image(api_instance, job_id: str, target_file: str):
    resp = api_instance.get_inference_job(
        job_id=job_id,
        headers={
            "x-api-key": config.api_key,
            "username": config.username
        },
    )

    if 'data' not in resp.json():
        raise Exception(f"data not found in inference job: {resp.json()}")

    if 'img_presigned_urls' not in resp.json()['data']:
        raise Exception(f"img_presigned_urls not found in inference job: {resp.json()}")

    if config.compare_content == 'false':
        logger.info(f"compare_content is false, skip comparing image {target_file}")
        return

    img_presigned_urls = resp.json()['data']['img_presigned_urls']

    for img_url in img_presigned_urls:
        resp = requests.get(img_url)

        with open(f"{target_file}", "wb") as f:
            f.write(resp.content)
            logger.info(f"Image {target_file} saved")


def get_inference_job_image(api_instance, job_id: str, target_file: str):
    resp = api_instance.get_inference_job(
        job_id=job_id,
        headers={
            "x-api-key": config.api_key,
            "username": config.username
        },
    )

    if 'data' not in resp.json():
        raise Exception(f"data not found in inference job: {resp.json()}")

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
            return

        # write image to file
        with open(f"{target_file}.png", "wb") as f:
            f.write(resp.content)

        logger.info(f"Image {target_file} not same with {target_file}.png")
        return
        # raise Exception(f"Image {target_file} different with {target_file}.png")

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
    logger.info(f"Uploading {local_path}")
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


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        # if passed in an object is instance of Decimal
        # convert it to a string
        if isinstance(obj, decimal.Decimal):
            return str(obj)

        # ️ otherwise use the default behavior
        return json.JSONEncoder.default(self, obj)


def comfy_execute_create(n, api, endpoint_name, wait_succeed=True,
                         workflow: str = './data/api_params/comfy_workflow.json'):
    with open(workflow, 'r') as f:
        headers = {
            "x-api-key": config.api_key,
        }
        prompt_id = str(uuid.uuid4())
        workflow = json.load(f)
        workflow['prompt_id'] = prompt_id
        workflow['endpoint_name'] = endpoint_name

        resp = api.create_execute(headers=headers, data=workflow)
        assert resp.status_code in [200, 201], resp.dumps()
        assert resp.json()['data']['prompt_id'] == prompt_id, resp.dumps()

        if not wait_succeed:
            return

        timeout = datetime.now() + timedelta(minutes=5)

        init_status = ''
        while datetime.now() < timeout:
            time.sleep(1)
            resp = api.get_execute_job(headers=headers, prompt_id=prompt_id)
            if resp.status_code == 404:
                init_status = "not found"
                logger.info(f"comfy {n} {endpoint_name} {prompt_id} is {init_status}")
                continue

            assert resp.status_code == 200, resp.dumps()

            assert 'status' in resp.json()['data'], resp.dumps()
            status = resp.json()["data"]["status"]

            if init_status != status:
                logger.info(f"comfy {n} {endpoint_name} {prompt_id} is {status}")
                init_status = status

            if status == 'success':
                resp = api.get_execute_job_logs(headers=headers, prompt_id=prompt_id)
                assert resp.status_code == 200, resp.dumps()
                break
            if status == InferenceStatus.FAILED.value:
                logger.error(resp.json())
                raise Exception(f"{n} {endpoint_name} {prompt_id} failed.")
        else:
            raise Exception(f"{n} {endpoint_name} {prompt_id} timed out after 5 minutes.")


def sd_inference_create(n, api, endpoint_name: str, workflow: str = './data/api_params/sd.json'):
    headers = {
        "x-api-key": config.api_key,
        "username": config.username
    }

    data = {
        "inference_type": "Async",
        "task_type": InferenceType.TXT2IMG.value,
        "models": {
            "Stable-diffusion": [config.default_model_id],
            "embeddings": []
        },
    }

    resp = api.create_inference(headers=headers, data=data)
    assert resp.status_code == 201, resp.dumps()

    inference_data = resp.json()['data']["inference"]
    inference_id = inference_data["id"]

    assert resp.json()["statusCode"] == 201
    assert inference_data["type"] == InferenceType.TXT2IMG.value
    assert len(inference_data["api_params_s3_upload_url"]) > 0

    upload_with_put(inference_data["api_params_s3_upload_url"], workflow)

    resp = api.get_inference_job(headers=headers, job_id=inference_data["id"])
    assert resp.status_code == 200, resp.dumps()

    resp = api.start_inference_job(job_id=inference_id, headers=headers)
    assert resp.status_code == 202, resp.dumps()

    assert resp.json()['data']["inference"]["status"] == InferenceStatus.INPROGRESS.value

    timeout = datetime.now() + timedelta(minutes=2)

    while datetime.now() < timeout:
        status = get_inference_job_status(
            api_instance=api,
            job_id=inference_id
        )
        logger.info(f"sd {n} {endpoint_name} {inference_id} is {status}")
        if status == InferenceStatus.SUCCEED.value:
            break
        if status == InferenceStatus.FAILED.value:
            logger.error(inference_data)
            break
        time.sleep(4)
    else:
        raise Exception(f"Inference {inference_id} timed out after 2 minutes.")


def base64_image(image_url: str):
    response = requests.get(image_url)
    image_data = response.content
    base64_encoded_image = base64.b64encode(image_data).decode('utf-8')
    return base64_encoded_image


def sd_inference_esi(api, workflow: str = './data/api_params/extra-single-image-api-params.json', image: str = None):
    headers = {
        "x-api-key": config.api_key,
        "username": config.username
    }

    data = {
        "inference_type": "Async",
        "task_type": InferenceType.ESI.value,
        "models": {
            "Stable-diffusion": [config.default_model_id],
            "embeddings": []
        },
    }

    resp = api.create_inference(headers=headers, data=data)
    assert resp.status_code == 201, resp.dumps()

    inference_data = resp.json()['data']["inference"]
    inference_id = inference_data["id"]

    assert resp.json()["statusCode"] == 201
    assert len(inference_data["api_params_s3_upload_url"]) > 0

    with open(workflow, 'rb') as data:
        if image:
            data = json.loads(data.read())
            data['image'] = image
        response = requests.put(inference_data["api_params_s3_upload_url"], data=json.dumps(data))
        response.raise_for_status()

    resp = api.get_inference_job(headers=headers, job_id=inference_data["id"])
    assert resp.status_code == 200, resp.dumps()

    resp = api.start_inference_job(job_id=inference_id, headers=headers)
    assert resp.status_code == 202, resp.dumps()

    assert resp.json()['data']["inference"]["status"] == InferenceStatus.INPROGRESS.value

    timeout = datetime.now() + timedelta(minutes=2)

    while datetime.now() < timeout:
        status = get_inference_job_status(
            api_instance=api,
            job_id=inference_id
        )
        logger.info(f"sd {inference_id} is {status}")
        if status == InferenceStatus.SUCCEED.value:
            break
        if status == InferenceStatus.FAILED.value:
            logger.error(inference_data)
            break
        time.sleep(4)
    else:
        raise Exception(f"Inference {inference_id} timed out after 2 minutes.")

    return inference_id


def sd_inference_rembg(api, workflow: str = './data/api_params/rembg-api-params.json', image: str = None):
    headers = {
        "x-api-key": config.api_key,
        "username": config.username
    }

    data = {
        "inference_type": "Async",
        "task_type": InferenceType.REMBG.value,
        "models": {
            "Stable-diffusion": [config.default_model_id],
            "embeddings": []
        },
    }

    resp = api.create_inference(headers=headers, data=data)
    assert resp.status_code == 201, resp.dumps()

    inference_data = resp.json()['data']["inference"]
    inference_id = inference_data["id"]

    assert resp.json()["statusCode"] == 201
    assert len(inference_data["api_params_s3_upload_url"]) > 0

    with open(workflow, 'rb') as data:
        if image:
            data = json.loads(data.read())
            data['input_image'] = image
        response = requests.put(inference_data["api_params_s3_upload_url"], data=json.dumps(data))
        response.raise_for_status()

    resp = api.get_inference_job(headers=headers, job_id=inference_data["id"])
    assert resp.status_code == 200, resp.dumps()

    resp = api.start_inference_job(job_id=inference_id, headers=headers)
    assert resp.status_code == 202, resp.dumps()

    assert resp.json()['data']["inference"]["status"] == InferenceStatus.INPROGRESS.value

    timeout = datetime.now() + timedelta(minutes=2)

    while datetime.now() < timeout:
        status = get_inference_job_status(
            api_instance=api,
            job_id=inference_id
        )
        logger.info(f"sd {inference_id} is {status}")
        if status == InferenceStatus.SUCCEED.value:
            break
        if status == InferenceStatus.FAILED.value:
            logger.error(inference_data)
            break
        time.sleep(4)
    else:
        raise Exception(f"Inference {inference_id} timed out after 2 minutes.")

    return inference_id


def get_endpoint_comfy_async(api):
    return get_endpoint_by_prefix(api, "comfy-async-")


def get_endpoint_comfy_real_time(api):
    return get_endpoint_by_prefix(api, "comfy-real-time-")


def get_endpoint_sd_async(api):
    return get_endpoint_by_prefix(api, "sd-async-")


def get_endpoint_sd_real_time(api):
    return get_endpoint_by_prefix(api, "sd-real-time-")


def get_endpoint_by_prefix(api, prefix: str):
    endpoints = list_endpoints(api)
    for endpoint in endpoints:
        if endpoint['endpoint_name'].startswith(prefix):
            return endpoint['endpoint_name']
    raise Exception(f"{prefix}* endpoint not found")


def endpoints_wait_for_in_service(api, endpoint_name: str = None):
    headers = {
        "x-api-key": config.api_key,
        "username": config.username
    }

    params = {
        "username": config.username
    }

    resp = api.list_endpoints(headers=headers, params=params)
    assert resp.status_code == 200, resp.dumps()

    for endpoint in resp.json()['data']["endpoints"]:
        if endpoint_name is not None and endpoint["endpoint_name"] != endpoint_name:
            continue

        endpoint_name = endpoint["endpoint_name"]

        if endpoint["endpoint_status"] == "Failed":
            raise Exception(f"{endpoint_name} is {endpoint['endpoint_status']}")

        if endpoint["endpoint_status"] != "InService":
            logger.info(f"{endpoint_name} is {endpoint['endpoint_status']}")
            return False
        else:
            return True

    return False


def check_s3_directory(directory):
    try:
        time.sleep(5)
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=config.bucket, Delimiter='/')

        for page in pages:
            if 'CommonPrefixes' in page:
                for prefix in page['CommonPrefixes']:
                    print(prefix['Prefix'])
                    if prefix['Prefix'].endswith(directory):
                        return True
        return False
    except (NoCredentialsError, PartialCredentialsError):
        print("Credentials not available.")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False
