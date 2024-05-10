from __future__ import print_function

import logging
import os
import threading
import time
import uuid

import pytest

import config as config
from utils.api import Api
from utils.helper import wget_file, comfy_execute_create, get_endpoint_comfy_async, get_endpoint_sd_async, \
    sd_inference_create

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

headers = {
    "x-api-key": config.api_key,
    "username": config.username
}

id = str(uuid.uuid4())


@pytest.mark.skipif(not config.is_local, reason="local test only")
class TestLatencyCompareTasks:
    def setup_class(self):
        self.api = Api(config)
        self.api.feat_oas_schema()
        self.endpoint_name = get_endpoint_comfy_async(self.api)
        self.endpoint_name_sd = get_endpoint_sd_async(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_1_download_file(self):
        local_path = f"./data/comfy/models/checkpoints/v1-5-pruned-emaonly.ckpt"
        wget_file(
            local_path,
            'https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.ckpt'
        )

    def test_2_sync_files_to_comfy_endpoint(self):
        local = "'./data/comfy/models/*'"
        target = f"'s3://{config.bucket}/comfy/{self.endpoint_name}/{id}/models/'"
        logger.info(f"Syncing {local} to {target}")
        os.system(f"rm -rf ./s5cmd")
        os.system(f"wget -q ./ https://raw.githubusercontent.com/elonniu/s5cmd/main/s5cmd")
        os.system(f"chmod +x ./s5cmd")
        os.system(f"./s5cmd sync {local} {target}")

    def test_3_comfy_sync_files(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }
        data = {"endpoint_name": f"{self.endpoint_name}",
                "need_reboot": True,
                "prepare_id": id,
                "prepare_type": "models"}
        resp = self.api.prepare(data=data, headers=headers)
        assert resp.status_code == 200, resp.dumps()
        logger.info(resp.json())
        logger.info(f"wait 20s for endpoint sync files...")
        time.sleep(20)

    def test_4_clean_all_executes(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        while True:
            resp = self.api.list_executes(headers=headers, params={"limit": 20})
            executes = resp.json()['data']['executes']
            if len(executes) == 0:
                break

            execute_id_list = []
            i = 0
            for execute in executes:
                i = i + 1
                prompt_id = execute['prompt_id']
                execute_id_list.append(prompt_id)
                logger.info(f"delete execute {i} {prompt_id}")

            data = {
                "execute_id_list": execute_id_list,
            }
            resp = self.api.delete_executes(headers=headers, data=data)
            if resp.status_code == 400:
                logger.info(resp.json()['message'])
                time.sleep(5)
                continue

    def test_6_clean_all_inferences(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        while True:

            resp = self.api.list_inferences(headers=headers, params={"limit": 20})
            inferences = resp.json()['data']['inferences']
            if len(inferences) == 0:
                break

            ids = []
            i = 0
            for inference in inferences:
                i = i + 1
                inference_id = inference['InferenceJobId']
                ids.append(inference_id)
                logger.info(f"delete execute {i} {inference_id}")

            data = {
                "inference_id_list": ids,
            }
            resp = self.api.delete_inferences(headers=headers, data=data)
            if resp.status_code == 400:
                logger.info(resp.json()['message'])
                time.sleep(5)
                continue

    def test_7_update_api_roles(self):
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

    def create_batch_executes(self, n, api, endpoint_name):
        for i in range(n):
            comfy_execute_create(n=i, api=api, endpoint_name=endpoint_name, wait_succeed=True,
                                 workflow='./data/api_params/latency-comfy.json')

    def create_batch_inferences(self, n, api, endpoint_name):
        for i in range(n):
            sd_inference_create(n=i, api=api, endpoint_name=endpoint_name, workflow='./data/api_params/latency-sd.json')

    def test_8_lantency_compare_start(self):
        self.test_7_update_api_roles()

        threads = []

        batch = 1000

        thread = threading.Thread(target=self.create_batch_executes, args=(batch, self.api, self.endpoint_name))
        threads.append(thread)

        thread = threading.Thread(target=self.create_batch_inferences, args=(batch, self.api, self.endpoint_name_sd))
        threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()
