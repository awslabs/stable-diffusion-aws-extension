from __future__ import print_function

import logging
import time
from datetime import datetime
from datetime import timedelta

import config as config
from utils.api import Api
from utils.enums import InferenceStatus, InferenceType
from utils.helper import upload_multipart_file, wget_file
from utils.helper import upload_with_put, get_inference_job_status

logger = logging.getLogger(__name__)
checkpoint_id = None
signed_urls = None

filename = "sd_xl_turbo_1.0_fp16.safetensors"
checkpoint_type = "Stable-diffusion"
inference_data = {}


class TestTurboE2E:

    def setup_class(self):
        self.api = Api(config)
        self.api.feat_oas_schema()

    @classmethod
    def teardown_class(self):
        pass

    def test_0_update_api_roles(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username,
        }

        data = {
            "username": "api",
            "password": "admin",
            "creator": "api",
            "roles": [
                'IT Operator',
                'byoc',
                config.role_sd_real_time,
                config.role_sd_async,
                config.role_comfy_async,
                config.role_comfy_real_time,
            ],
        }

        resp = self.api.create_user(headers=headers, data=data)

        assert resp.status_code == 201, resp.dumps()
        assert resp.json()["statusCode"] == 201

    def test_0_delete_checkpoints_turbo(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username,
        }

        resp = self.api.list_checkpoints(headers=headers)
        assert resp.status_code == 200, resp.dumps()
        ckpts = resp.json()['data']['checkpoints']

        for ckpt in ckpts:
            if ckpt['name'][0] == filename:
                data = {
                    "checkpoint_id_list": [ckpt['id']]
                }
                resp = self.api.delete_checkpoints(headers=headers, data=data)
                assert resp.status_code == 204, resp.dumps()

    def test_1_create_turbo_checkpoint(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username,
        }

        data = {
            "checkpoint_type": checkpoint_type,
            "filenames": [
                {
                    "filename": filename,
                    "parts_number": 7
                }
            ],
            "params": {
                "message": config.ckpt_message,
                "creator": config.username
            }
        }

        resp = self.api.create_checkpoint(headers=headers, data=data)

        assert resp.status_code == 201, resp.dumps()

        assert resp.json()["statusCode"] == 201
        assert resp.json()['data']["checkpoint"]['type'] == checkpoint_type
        assert len(resp.json()['data']["checkpoint"]['id']) == 36

        global checkpoint_id
        checkpoint_id = resp.json()['data']["checkpoint"]['id']
        global signed_urls
        signed_urls = resp.json()['data']["s3PresignUrl"][filename]

    def test_2_update_turbo_checkpoint(self):
        local_path = f"/tmp/test/models/Stable-diffusion/{filename}"
        wget_file(
            local_path,
            'https://huggingface.co/stabilityai/sdxl-turbo/resolve/main/sd_xl_turbo_1.0_fp16.safetensors',
            'https://aws-gcr-solutions.s3.cn-north-1.amazonaws.com.cn/stable-diffusion-aws-extension-github-mainline/models/sd_xl_turbo_1.0_fp16.safetensors'
        )
        global signed_urls
        multiparts_tags = upload_multipart_file(signed_urls, local_path)

        global checkpoint_id

        data = {
            "status": "Active",
            "multi_parts_tags": {filename: multiparts_tags}
        }

        headers = {
            "x-api-key": config.api_key,
        }

        resp = self.api.update_checkpoint(checkpoint_id=checkpoint_id, headers=headers, data=data)

        assert resp.status_code == 200, resp.dumps()
        assert resp.json()["statusCode"] == 200
        assert resp.json()['data']["checkpoint"]['type'] == checkpoint_type

    def test_3_list_turbo_checkpoint(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username,
        }

        params = {
            "username": config.username
        }

        resp = self.api.list_checkpoints(headers=headers, params=params)
        assert resp.status_code == 200, resp.dumps()
        global checkpoint_id
        assert checkpoint_id in [checkpoint["id"] for checkpoint in resp.json()['data']["checkpoints"]]

    def test_4_turbo_txt2img_async_job_create(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        data = {
            "inference_type": "Async",
            "task_type": InferenceType.TXT2IMG.value,
            "models": {
                "Stable-diffusion": [filename],
                "embeddings": []
            },
        }

        resp = self.api.create_inference(headers=headers, data=data)
        assert resp.status_code == 201, resp.dumps()
        global inference_data
        inference_data = resp.json()['data']["inference"]

        assert resp.json()["statusCode"] == 201
        assert inference_data["type"] == InferenceType.TXT2IMG.value
        assert len(inference_data["api_params_s3_upload_url"]) > 0

        upload_with_put(inference_data["api_params_s3_upload_url"], "./data/api_params/turbo_api_param.json")

    def test_5_turbo_txt2img_async_job_succeed(self):
        global inference_data
        assert inference_data["type"] == InferenceType.TXT2IMG.value

        inference_id = inference_data["id"]

        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        resp = self.api.start_inference_job(job_id=inference_id, headers=headers)
        assert resp.status_code == 202, resp.dumps()
        assert resp.json()['data']["inference"]["status"] == InferenceStatus.INPROGRESS.value

        timeout = datetime.now() + timedelta(minutes=4)

        while datetime.now() < timeout:
            status = get_inference_job_status(
                api_instance=self.api,
                job_id=inference_id
            )
            logger.info(f"sd xl turbo Async is {status}")
            if status == InferenceStatus.SUCCEED.value:
                break
            if status == InferenceStatus.FAILED.value:
                logger.error(resp.dumps())
                logger.error(inference_data)
                # break
                raise Exception(f"Inference job {inference_id} failed.")
            time.sleep(5)
        else:
            raise Exception("Inference timed out after 4 minutes.")
