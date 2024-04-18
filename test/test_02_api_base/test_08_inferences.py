from __future__ import print_function

import logging

import config as config
from utils.api import Api
from utils.enums import InferenceType
from utils.helper import update_oas

logger = logging.getLogger(__name__)


class TestInferencesApi:
    @classmethod
    def setup_class(self):
        self.api = Api(config)
        update_oas(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_1_create_inference_without_key(self):
        resp = self.api.create_inference()

        assert resp.status_code == 403, resp.dumps()

    def test_2_create_inference_without_auth(self):
        data = {
            "task_type": "txt2img",
            "inference_type": "Async",
            "models": {
                "Stable-diffusion": [config.default_model_id],
                "embeddings": []
            },
        }

        resp = self.api.create_inference(data=data)

        assert resp.status_code == 403, resp.dumps()

    def test_3_create_inference_with_bad_params(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        data = {
            "bad_param": "bad_param",
        }

        resp = self.api.create_inference(headers=headers, data=data)

        assert 'object has missing required properties' in resp.json()['message']

    def test_4_list_inferences_without_key(self):
        resp = self.api.list_inferences()

        assert resp.status_code == 403, resp.dumps()

    def test_5_list_inferences_without_auth(self):
        headers = {"x-api-key": config.api_key}

        resp = self.api.list_inferences(headers=headers)

        assert resp.status_code == 200, resp.dumps()

    def test_6_delete_inferences_with_bad_request_body(self):
        headers = {
            "x-api-key": config.api_key,
        }

        data = {
            "bad": ['bad'],
        }

        resp = self.api.delete_inferences(headers=headers, data=data)

        assert 'object has missing required properties' in resp.json()["message"]
        assert 'inference_id_list' in resp.json()["message"]

    def test_7_delete_inferences_without_key(self):
        headers = {}

        data = {
            "bad": ['bad'],
        }

        resp = self.api.delete_inferences(headers=headers, data=data)
        assert resp.status_code == 403, resp.dumps()

    def test_8_delete_inferences_succeed(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        data = {
            "inference_id_list": ['bad'],
        }

        resp = self.api.delete_inferences(headers=headers, data=data)
        assert resp.status_code == 204, resp.dumps()

    def test_9_get_inference_job_without_key(self):
        resp = self.api.get_inference_job(job_id="job_id")
        assert resp.status_code == 403, resp.dumps()

    def test_10_get_inference_job_not_found(self):
        headers = {
            "x-api-key": config.api_key,
        }

        job_id = "not_exists"

        resp = self.api.get_inference_job(job_id=job_id, headers=headers)
        assert resp.status_code == 404, resp.dumps()
        assert f'inference with id {job_id} not found' == resp.json()["message"]

    def test_11_one_api_payload_string_check(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        payload = {
            "inference_type": "Real-time",
            "task_type": InferenceType.TXT2IMG.value,
            "models": {
                "Stable-diffusion": ["filename"],
                "embeddings": []
            },
            "payload_string": "string"

        }

        resp = self.api.create_inference(data=payload, headers=headers)
        assert resp.json()['message'] == 'payload_string must be valid json string', resp.dumps()
