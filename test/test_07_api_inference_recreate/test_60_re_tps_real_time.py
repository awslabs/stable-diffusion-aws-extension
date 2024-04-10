from __future__ import print_function

import logging
import threading

import config as config
from utils.api import Api
from utils.enums import InferenceType
from utils.helper import upload_with_put, update_oas

logger = logging.getLogger(__name__)

inference_data = {}
ids = []


def task_to_run(inference_id):
    t_name = threading.current_thread().name
    print(f"\nTask is running on thread: {t_name}, {inference_id}")

    headers = {
        "x-api-key": config.api_key,
        "username": config.username
    }
    api = Api(config)

    resp = api.start_inference_job(job_id=inference_id, headers=headers)
    assert resp.status_code == 200, resp.dumps()
    assert 'img_presigned_urls' in resp.json()['data'], resp.dumps()
    assert len(resp.json()['data']['img_presigned_urls']) > 0, resp.dumps()


class TestTpsRealTimeE2E:

    def setup_class(self):
        self.api = Api(config)
        update_oas(self.api)

    @classmethod
    def teardown_class(cls):
        pass

    def test_0_clear_inferences_jobs(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }
        resp = self.api.list_inferences(headers)
        assert resp.status_code == 200, resp.dumps()
        inferences = resp.json()['data']['inferences']
        list = []
        for inference in inferences:
            list.append(inference['InferenceJobId'])
        data = {
            "inference_id_list": list
        }
        self.api.delete_inferences(data=data, headers=headers)

    def test_1_start_real_time_tps(self):

        ids = []
        for i in range(20):
            ids.append(self.tps_inference_real_time_create())

        threads = []
        for id in ids:
            thread = threading.Thread(target=task_to_run, args=(id,))
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

    def tps_inference_real_time_create(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        data = {
            "inference_type": "Real-time",
            "task_type": InferenceType.TXT2IMG.value,
            "models": {
                "Stable-diffusion": [config.default_model_id],
                "embeddings": []
            },
        }

        resp = self.api.create_inference(headers=headers, data=data)
        assert resp.status_code == 201, resp.dumps()

        global inference_data
        inference_data = resp.json()['data']["inference"]

        assert resp.json()["statusCode"] == 201

        assert len(inference_data["api_params_s3_upload_url"]) > 0

        upload_with_put(inference_data["api_params_s3_upload_url"], "./data/api_params/txt2img_api_param.json")
        return inference_data['id']
