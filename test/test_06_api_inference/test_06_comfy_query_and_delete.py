import json
import logging
import uuid

import config as config
from utils.api import Api
from utils.helper import update_oas

logger = logging.getLogger(__name__)


class TestTxt2ImgReQueryAndDeleteComfyE2E:

    def setup_class(self):
        self.api = Api(config)
        update_oas(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_1_comfy_txt2img_async_batch_create(self):
        count = 20
        for i in range(count):
            self.comfy_txt2img_async_create()

    def comfy_txt2img_async_create(self):
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
            "prompt_id": str(uuid.uuid4()),
            "endpoint_name": config.comfy_async_ep_name
        })

        resp = self.api.create_execute(headers=headers, data=json.loads(payload))
        assert resp.json()["statusCode"] == 201
        logger.info(f"execute created: {resp.json()['data']['prompt_id']}")

    def test_2_comfy_txt2img_list(self):
        last_evaluated_key = None
        while True:
            resp = self.executes_list(exclusive_start_key=last_evaluated_key)
            last_evaluated_key = resp.json()['data']['last_evaluated_key']
            logger.info(last_evaluated_key)
            if not last_evaluated_key:
                break

    def executes_list(self, exclusive_start_key=None):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        resp = self.api.list_executes(headers=headers,
                                      params={"exclusive_start_key": exclusive_start_key, "limit": 20})
        return resp

    def test_4_comfy_txt2img_clean(self):
        last_evaluated_key = None
        while True:
            resp = self.executes_list(exclusive_start_key=last_evaluated_key)
            executes = resp.json()['data']['executes']
            last_evaluated_key = resp.json()['data']['last_evaluated_key']

            for execute in executes:
                prompt_id = execute['prompt_id']
                headers = {
                    "x-api-key": config.api_key,
                    "username": config.username
                }
                data = {
                    "execute_id_list": [prompt_id]
                }
                resp = self.api.delete_executes(headers=headers, data=data)
                assert resp.status_code == 204, resp.dumps()
                logger.info(f"deleted prompt_id: {prompt_id}")

            if not last_evaluated_key:
                break

    def test_5_comfy_txt2img_check_clean(self):
        resp = self.executes_list()
        executes = resp.json()['data']['executes']
        assert len(executes) == 0, resp.dumps()
