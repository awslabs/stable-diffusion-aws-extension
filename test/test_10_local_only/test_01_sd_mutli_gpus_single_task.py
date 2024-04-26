from __future__ import print_function

import logging

import pytest

import config as config
from utils.api import Api
from utils.enums import InferenceType
from utils.helper import update_oas, upload_with_put

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

headers = {
    "x-api-key": config.api_key,
    "username": config.username
}

inference_id = ''


@pytest.mark.skipif(not config.is_local, reason="local test only")
class TestMutilGPUsSingleTask:
    def setup_class(self):
        self.api = Api(config)
        update_oas(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_0_gpus_clear_inferences_jobs(self):
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

    def test_2_create_job(self):
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

        upload_with_put(inference_data["api_params_s3_upload_url"],
                        "./data/api_params/txt2img_api_param_batch_size.json")
        global inference_id
        inference_id = inference_data['id']

    def test_3_gpus_start_real_time_tps(self):
        global inference_id

        self.api.start_inference_job(job_id=inference_id, headers=headers)
        logger.info(f"infer_id: {inference_id}")
