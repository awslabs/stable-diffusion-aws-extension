from __future__ import print_function

import base64
import logging
import os

import config as config
from utils.api import Api
from utils.helper import get_inference_image, sd_inference_rembg

logger = logging.getLogger(__name__)


class TestRembgInferenceAsyncBatchE2E:

    def setup_class(self):
        self.api = Api(config)
        self.api.feat_oas_schema()

    @classmethod
    def teardown_class(cls):
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

    def test_1_rembg_batch(self):
        for root, dirs, files in os.walk('./data/images/'):
            for file in files:
                file_path = os.path.join(root, file)
                if file_path.endswith(".jpg"):
                    with open(file_path, "rb") as image_file:
                        image = base64.b64encode(image_file.read()).decode('utf-8')
                        inference_id = sd_inference_rembg(self.api, image=image)
                        get_inference_image(
                            api_instance=self.api,
                            job_id=inference_id,
                            target_file=f"{file_path}.new.png"
                        )
