from __future__ import print_function

import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timedelta

import pytest

import config as config
from utils.api import Api
from utils.enums import InferenceStatus
from utils.helper import update_oas, wget_file

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

headers = {
    "x-api-key": config.api_key,
    "username": config.username
}

prompt_id = "222222-22222-2222"


def tps_async_create(api):
    headers = {
        "x-api-key": config.api_key,
    }

    with open("./data/api_params/comfy_workflow.json", 'rb') as data:
        file_content = data.read()
        file_content = json.loads(file_content)
        print(file_content)

    return
    payload = json.dumps({
        "need_sync": True,
        "prompt": {
            "4": {
                "inputs": {
                    "ckpt_name": "sdXL_v10VAEFix.safetensors"
                },
                "class_type": "CheckpointLoaderSimple"
            },
            "5": {
                "inputs": {
                    "width": 1024,
                    "height": 1024,
                    "batch_size": 1
                },
                "class_type": "EmptyLatentImage"
            },
            "6": {
                "inputs": {
                    "text": "evening sunset scenery blue sky nature, glass bottle with a galaxy in it",
                    "clip": [
                        "4",
                        1
                    ]
                },
                "class_type": "CLIPTextEncode"
            },
            "7": {
                "inputs": {
                    "text": "text, watermark",
                    "clip": [
                        "4",
                        1
                    ]
                },
                "class_type": "CLIPTextEncode"
            },
            "10": {
                "inputs": {
                    "add_noise": "enable",
                    "noise_seed": 721897303308196,
                    "steps": 25,
                    "cfg": 8,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "start_at_step": 0,
                    "end_at_step": 20,
                    "return_with_leftover_noise": "enable",
                    "model": [
                        "4",
                        0
                    ],
                    "positive": [
                        "6",
                        0
                    ],
                    "negative": [
                        "7",
                        0
                    ],
                    "latent_image": [
                        "5",
                        0
                    ]
                },
                "class_type": "KSamplerAdvanced"
            },
            "11": {
                "inputs": {
                    "add_noise": "disable",
                    "noise_seed": 0,
                    "steps": 25,
                    "cfg": 8,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "start_at_step": 20,
                    "end_at_step": 10000,
                    "return_with_leftover_noise": "disable",
                    "model": [
                        "12",
                        0
                    ],
                    "positive": [
                        "15",
                        0
                    ],
                    "negative": [
                        "16",
                        0
                    ],
                    "latent_image": [
                        "10",
                        0
                    ]
                },
                "class_type": "KSamplerAdvanced"
            },
            "12": {
                "inputs": {
                    "ckpt_name": "sdXL_v10VAEFix.safetensors"
                },
                "class_type": "CheckpointLoaderSimple"
            },
            "15": {
                "inputs": {
                    "text": "evening sunset scenery blue sky nature, glass bottle with a galaxy in it",
                    "clip": [
                        "12",
                        1
                    ]
                },
                "class_type": "CLIPTextEncode"
            },
            "16": {
                "inputs": {
                    "text": "text, watermark",
                    "clip": [
                        "12",
                        1
                    ]
                },
                "class_type": "CLIPTextEncode"
            },
            "17": {
                "inputs": {
                    "samples": [
                        "11",
                        0
                    ],
                    "vae": [
                        "12",
                        2
                    ]
                },
                "class_type": "VAEDecode"
            },
            "19": {
                "inputs": {
                    "filename_prefix": "ComfyUI",
                    "images": [
                        "17",
                        0
                    ]
                },
                "class_type": "SaveImage"
            }
        },
        "prompt_id": str(uuid.uuid4()),
        "endpoint_name": config.comfy_async_ep_name
    })

    resp = api.create_execute(headers=headers, data=json.loads(payload))
    assert resp.status_code == 201, resp.dumps()

    inference_data = resp.json()['data']

    assert resp.json()["statusCode"] == 201
    print(json.dumps(resp.json()['debug'], indent=2))

    prompt_id = inference_data["prompt_id"]

    timeout = datetime.now() + timedelta(minutes=5)

    while datetime.now() < timeout:
        resp = api.get_execute_job(headers=headers, prompt_id=prompt_id)
        status = resp.json()["data"]["status"]
        logger.info(f"execute {prompt_id} is {status}")
        if status == 'success':
            break
        if status == InferenceStatus.FAILED.value:
            logger.error(inference_data)
            raise Exception(f"execute {prompt_id} failed.")
        time.sleep(7)
    else:
        raise Exception(f"execute {prompt_id} timed out after 5 minutes.")


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
        threads = []
        for i in range(1):
            thread = threading.Thread(target=tps_async_create, args=(self.api,))
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()
