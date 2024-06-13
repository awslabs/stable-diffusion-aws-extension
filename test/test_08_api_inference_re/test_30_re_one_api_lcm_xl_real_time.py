import json
import logging

import config as config
from utils.api import Api
from utils.enums import InferenceType

logger = logging.getLogger(__name__)

filename = "v1-5-pruned-emaonly.safetensors"
lora_filename = "lcm_lora_xl.safetensors"


class TestInferenceOneApiLcmXLRealTimeE2E:

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

    def test_1_one_api_lcm_xl_real_time(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        payload = {
            "inference_type": "Real-time",
            "task_type": InferenceType.TXT2IMG.value,
            "models": {
                "Stable-diffusion": [filename],
                "Lora": [lora_filename],
                "embeddings": []
            },

        }

        with open("./data/api_params/txt2img_lcm_xl_api_param.json", 'rb') as data:
            payload["payload_string"] = json.dumps(json.loads(data.read()))
            resp = self.api.create_inference(data=payload, headers=headers)
            assert resp.status_code == 200, resp.dumps()
            result = resp.json()['data']
            assert 'img_presigned_urls' in result, f'img_presigned_urls not found in {result}'
