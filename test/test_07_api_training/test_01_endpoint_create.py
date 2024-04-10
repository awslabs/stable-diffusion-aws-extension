import logging
from time import sleep

import pytest

import config as config
from utils.api import Api
from utils.helper import delete_sagemaker_endpoint, get_endpoint_status, update_oas

logger = logging.getLogger(__name__)


@pytest.mark.skipif(config.is_gcr, reason="not ready in gcr")
class TestEndpointCreateForTrainE2E:

    def setup_class(self):
        self.api = Api(config)
        update_oas(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_1_endpoints_async_delete_before(self):
        endpoint_name = f"sd-async-{config.endpoint_name}"
        while True:
            status = get_endpoint_status(self.api, endpoint_name)
            if status is None:
                break

            if status in ['Creating', 'Updating']:
                logger.warning(f"Endpoint {endpoint_name} is {status}, waiting to delete...")
                sleep(10)
            else:
                try:
                    delete_sagemaker_endpoint(self.api, endpoint_name)
                    break
                except Exception as e:
                    sleep(2)
                    logger.info(e)
        pass

    def test_2_endpoints_real_time_delete_before(self):
        endpoint_name = f"sd-real-time-{config.endpoint_name}"
        while True:
            status = get_endpoint_status(self.api, endpoint_name)
            if status is None:
                break

            if status in ['Creating', 'Updating']:
                logger.warning(f"Endpoint {endpoint_name} is {status}, waiting to delete...")
                sleep(10)
            else:
                try:
                    delete_sagemaker_endpoint(self.api, endpoint_name)
                    break
                except Exception as e:
                    sleep(2)
                    logger.info(e)
        pass

    def test_2_no_available_endpoint(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        params = {
            "username": config.username
        }

        list = self.api.list_endpoints(headers=headers, params=params)

        if 'endpoints' in list and len(list['data']["endpoints"]) > 0:
            return

        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        data = {
            "task_type": "txt2img",
            "inference_type": "Async",
            "models": {
                "Stable-diffusion": [config.default_model_id],
                "embeddings": []
            },
        }

        resp = self.api.create_inference(headers=headers, data=data)
        assert resp.json()["message"] == 'no available Async endpoints for user "api"'

    def test_3_create_endpoint_async(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        data = {
            "endpoint_name": config.endpoint_name,
            "endpoint_type": "Async",
            "service_type": "sd",
            "instance_type": config.async_instance_type,
            "initial_instance_count": 1,
            "autoscaling_enabled": True,
            "assign_to_roles": ["IT Operator"],
            "creator": config.username
        }

        resp = self.api.create_endpoint(headers=headers, data=data)
        assert 'data' in resp.json(), resp.dumps()
        assert resp.json()["data"]["endpoint_status"] == "Creating", resp.dumps()

    def test_4_create_endpoint_real_time(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        data = {
            "endpoint_name": config.endpoint_name,
            "endpoint_type": "Real-time",
            "service_type": "sd",
            "instance_type": config.real_time_instance_type,
            "initial_instance_count": 1,
            "autoscaling_enabled": False,
            "assign_to_roles": ["byoc"],
            "creator": config.username
        }

        resp = self.api.create_endpoint(headers=headers, data=data)
        assert 'data' in resp.json(), resp.dumps()
        assert resp.json()["data"]["endpoint_status"] == "Creating", resp.dumps()

    def test_5_create_endpoint_exists(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        data = {
            "endpoint_name": config.endpoint_name,
            "endpoint_type": 'Async',
            "instance_type": config.async_instance_type,
            "initial_instance_count": int(config.initial_instance_count),
            "autoscaling_enabled": False,
            "assign_to_roles": ["Designer"],
            "creator": config.username
        }

        resp = self.api.create_endpoint(headers=headers, data=data)
        assert "Cannot create already existing model" in resp.json()["message"]
