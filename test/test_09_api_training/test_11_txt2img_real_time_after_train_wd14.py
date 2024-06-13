from __future__ import print_function

import logging

import pytest

import config as config
from utils.api import Api
from utils.enums import InferenceType, InferenceStatus
from utils.helper import upload_with_put

logger = logging.getLogger(__name__)

inference_data = {}


@pytest.mark.skipif(config.is_gcr, reason="not ready in gcr")
@pytest.mark.skipif(config.test_fast, reason="test_fast")
class TestTxt2ImgRealtimeAfterTrainWd14E2E:

    def setup_class(self):
        self.api = Api(config)
        self.api.feat_oas_schema()

    @classmethod
    def teardown_class(self):
        pass

    def test_1_after_train_txt2img_real_time_create(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        data = {
            "inference_type": "Real-time",
            "task_type": InferenceType.TXT2IMG.value,
            "models": {
                "Stable-diffusion": [config.default_model_id],
                "VAE": ["Automatic"],
                "Lora": [f"{config.train_wd14_model_name}.safetensors"],
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

        upload_with_put(inference_data["api_params_s3_upload_url"], "./data/api_params/txt2img_api_param_train.json")

    def test_2_txt2img_real_time_start_and_succeed(self):
        global inference_data
        assert inference_data["type"] == InferenceType.TXT2IMG.value

        inference_id = inference_data["id"]

        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        resp = self.api.start_inference_job(job_id=inference_id, headers=headers)
        assert resp.status_code in [200, 504], resp.dumps()
        if resp.status_code == 504:
            import time
            time.sleep(60)

    def test_3_txt2img_real_time_exists(self):
        global inference_data
        assert inference_data["type"] == InferenceType.TXT2IMG.value

        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        resp = self.api.get_inference_job(headers=headers, job_id=inference_data["id"])
        assert resp.status_code == 200, resp.dumps()

        assert resp.json()['data']['status'] == InferenceStatus.SUCCEED.value, resp.dumps()

    def test_4_txt2img_real_time_delete_succeed(self):
        global inference_data
        assert inference_data["type"] == InferenceType.TXT2IMG.value

        inference_id = inference_data["id"]

        headers = {
            "x-api-key": config.api_key
        }

        data = {
            "inference_id_list": [inference_id],
        }

        resp = self.api.delete_inferences(headers=headers, data=data)
        assert resp.status_code == 204, resp.dumps()
