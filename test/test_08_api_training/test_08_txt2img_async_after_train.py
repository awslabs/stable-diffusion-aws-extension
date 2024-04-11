from __future__ import print_function

import logging
import time
from datetime import datetime
from datetime import timedelta

import pytest

import config as config
from utils.api import Api
from utils.enums import InferenceStatus, InferenceType
from utils.helper import upload_with_put, get_inference_job_status, update_oas

logger = logging.getLogger(__name__)

inference_data = {}


@pytest.mark.skipif(config.is_gcr, reason="not ready in gcr")
@pytest.mark.skipif(config.test_fast, reason="test_fast")
class TestTxt2ImgInferenceAsyncAfterTrainE2E:

    def setup_class(self):
        self.api = Api(config)
        update_oas(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_1_txt2img_inference_async_create(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        data = {
            "inference_type": "Async",
            "task_type": InferenceType.TXT2IMG.value,
            "models": {
                "Stable-diffusion": [config.default_model_id],
                "VAE": ["Automatic"],
                "Lora": [f"{config.train_model_name}.safetensors"],
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

    def test_2_txt2img_inference_async_exists(self):
        global inference_data
        assert inference_data["type"] == InferenceType.TXT2IMG.value

        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        resp = self.api.get_inference_job(headers=headers, job_id=inference_data["id"])
        assert resp.status_code == 200, resp.dumps()

    def test_3_txt2img_inference_async_start_and_succeed(self):
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

        timeout = datetime.now() + timedelta(minutes=7)

        while datetime.now() < timeout:
            status = get_inference_job_status(
                api_instance=self.api,
                job_id=inference_id
            )
            logger.info(f"txt2img_inference_async is {status}")
            if status == InferenceStatus.SUCCEED.value:
                break
            if status == InferenceStatus.FAILED.value:
                logger.error(inference_data)
                raise Exception(f"Inference job {inference_id} failed.")
            time.sleep(7)
        else:
            raise Exception(f"Inference execution {inference_id} timed out after 7 minutes.")

    def test_4_txt2img_inference_async_delete_succeed(self):

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
