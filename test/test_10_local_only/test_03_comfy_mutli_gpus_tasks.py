from __future__ import print_function

import logging
import os
import threading

import pytest

import config as config
from utils.api import Api
from utils.enums import InferenceType
from utils.helper import update_oas, upload_with_put, wget_file

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

headers = {
    "x-api-key": config.api_key,
    "username": config.username
}


def task_to_run(inference_id):
    t_name = threading.current_thread().name
    logger.info(f"Task is running on {t_name}, {inference_id}")

    api = Api(config)

    api.start_inference_job(job_id=inference_id, headers=headers)
    logger.info(f"start_inference_job: {inference_id}")


@pytest.mark.skipif(not config.is_local, reason="local test only")
class TestComfyMutilTaskGPUs:
    def setup_class(self):
        self.api = Api(config)
        self.endpoint_name = self.get_ep()
        update_oas(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def get_ep(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        params = {
            "username": config.username
        }

        resp = self.api.list_endpoints(headers=headers, params=params)
        assert resp.status_code == 200, resp.dumps()

        endpoints = resp.json()['data']["endpoints"]
        assert len(endpoints) >= 0
        return endpoints[0]['endpoint_name']

    def test_10_download_file(self):
        local_path = f"./data/comfy/checkpoints/v1-5-pruned-emaonly.ckpt"
        wget_file(
            local_path,
            'https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.ckpt'
        )

    def test_11_sync_files_to_comfy_endpoint(self):
        local = "'./data/comfy/*'"
        target = f"'s3://{config.bucket}/comfy/{self.endpoint_name}/{id}/models/'"
        logger.info(f"Syncing {local} to {target}")
        os.system(f"rm -rf ./s5cmd")
        os.system(f"wget -q ./ https://raw.githubusercontent.com/elonniu/s5cmd/main/s5cmd")
        os.system(f"chmod +x ./s5cmd")
        os.system(f"./s5cmd sync {local} {target}")

    def test_12_sync_files(self):
        data = {"endpoint_name": f"{self.endpoint_name}",
                "need_reboot": True,
                "prepare_id": id,
                "prepare_type": "models"}
        self.api.prepare(data=data)

    def test_13_comfy_gpus_clear_inferences_jobs(self):
        resp = self.api.list_inferences(headers, params={"limit": 100})
        assert resp.status_code == 200, resp.dumps()
        inferences = resp.json()['data']['inferences']
        list = []
        for inference in inferences:
            list.append(inference['InferenceJobId'])
        data = {
            "inference_id_list": list
        }
        self.api.delete_inferences(data=data, headers=headers)

    def test_14_comfy_gpus_start_async_tps(self):
        ids = []
        for i in range(20):
            id = self.tps_async_create()
            logger.info(f"inference created: {id}")
            ids.append(id)

        threads = []
        for id in ids:
            thread = threading.Thread(target=task_to_run, args=(id,))
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

    def tps_async_create(self):
        data = {
            "inference_type": "Async",
            "task_type": InferenceType.TXT2IMG.value,
            "models": {
                "Stable-diffusion": [config.default_model_id],
                "embeddings": []
            },
        }

        resp = self.api.create_inference(headers=headers, data=data)
        assert resp.status_code == 201, resp.dumps()

        inference_data = resp.json()['data']["inference"]

        upload_with_put(inference_data["api_params_s3_upload_url"], "./data/api_params/txt2img_api_param.json")

        return inference_data['id']
