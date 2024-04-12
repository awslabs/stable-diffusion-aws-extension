import json
import logging
import time
from datetime import datetime
from datetime import timedelta

import config as config
from utils.api import Api
from utils.enums import InferenceStatus
from utils.helper import update_oas

logger = logging.getLogger(__name__)

inference_data = {}

prompt_id = "11111111-1111-1111"


class TestTxt2ImgInferenceAsyncAfterComfyE2E:

    def setup_class(self):
        self.api = Api(config)
        update_oas(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_1_comfy_txt2img_async_create(self):
        headers = {
            "x-api-key": config.api_key,
        }

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
            "prompt_id": prompt_id,
            "endpoint_name": config.comfy_async_ep_name
        })

        resp = self.api.create_execute(headers=headers, data=json.loads(payload))
        assert resp.status_code == 201, resp.dumps()

        global inference_data
        inference_data = resp.json()['data']

        assert resp.json()["statusCode"] == 201
        print(json.dumps(resp.json()['debug'], indent=2))

    def test_2_comfy_txt2img_async_exists(self):
        global inference_data
        prompt_id = inference_data["prompt_id"]

        headers = {
            "x-api-key": config.api_key,
        }

        resp = self.api.get_execute_job(headers=headers, prompt_id=prompt_id)
        assert resp.status_code == 200, resp.dumps()

    def test_3_comfy_txt2img_async_start_and_succeed(self):

        headers = {
            "x-api-key": config.api_key,
        }

        global inference_data
        prompt_id = inference_data["prompt_id"]

        timeout = datetime.now() + timedelta(minutes=7)

        while datetime.now() < timeout:
            resp = self.api.get_execute_job(headers=headers, prompt_id=prompt_id)
            status = resp.json()["data"]["status"]
            logger.info(f"execute {prompt_id} is {status}")
            if status == 'success':
                break
            if status == InferenceStatus.FAILED.value:
                logger.error(inference_data)
                raise Exception(f"execute {prompt_id} failed.")
            time.sleep(7)
        else:
            raise Exception(f"execute {prompt_id} timed out after 7 minutes.")
