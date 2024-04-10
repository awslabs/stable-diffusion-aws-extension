import logging
from time import sleep

import config as config
from utils.api import Api
from utils.helper import delete_sagemaker_endpoint, get_endpoint_status, update_oas

logger = logging.getLogger(__name__)


class TestEndpointCreateForComfyE2E:

    def setup_class(self):
        self.api = Api(config)
        update_oas(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_1_clean_all_endpoints(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        resp = self.api.list_endpoints(headers=headers)

        endpoints = resp.json()['data']['endpoints']
        for endpoint in endpoints:
            endpoint_name = endpoint['endpoint_name']
            while True:
                data = {
                    "endpoint_name_list": [
                        endpoint_name
                    ],
                }
                resp = self.api.delete_endpoints(headers=headers, data=data)
                if resp.status_code == 400:
                    logger.info(resp.json()['message'])
                    sleep(5)
                    continue
                else:
                    break

    def test_1_endpoints_async_delete_before(self):
        while True:
            status = get_endpoint_status(self.api, config.comfy_async_ep_name)
            if status is None:
                break

            if status in ['Creating', 'Updating']:
                logger.warning(f"Endpoint {config.comfy_async_ep_name} is {status}, waiting to delete...")
                sleep(10)
            else:
                try:
                    delete_sagemaker_endpoint(self.api, config.comfy_async_ep_name)
                    break
                except Exception as e:
                    logger.info(e)
                    sleep(2)
        pass

    def test_2_endpoints_real_time_delete_before(self):
        while True:
            status = get_endpoint_status(self.api, config.comfy_real_time_ep_name)
            if status is None:
                break

            if status in ['Creating', 'Updating']:
                logger.warning(f"Endpoint {config.comfy_real_time_ep_name} is {status}, waiting to delete...")
                sleep(10)
            else:
                delete_sagemaker_endpoint(self.api, config.comfy_real_time_ep_name)
                break
        pass

    def test_2_no_available_endpoint_for_comfy(self):
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

    def test_3_create_endpoint_async_for_comfy(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        data = {
            "endpoint_name": "test",
            "service_type": "comfy",
            "endpoint_type": "Async",
            "instance_type": config.async_instance_type,
            "initial_instance_count": 1,
            "autoscaling_enabled": True,
            "assign_to_roles": ["comfy"],
            "creator": config.username
        }

        resp = self.api.create_endpoint(headers=headers, data=data)
        assert 'data' in resp.json(), resp.dumps()
        assert resp.json()["data"]["endpoint_status"] == "Creating", resp.dumps()

    def test_4_create_endpoint_real_time_for_comfy(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        data = {
            "endpoint_name": "test",
            "service_type": "comfy",
            "endpoint_type": "Real-time",
            "instance_type": config.real_time_instance_type,
            "initial_instance_count": 1,
            "autoscaling_enabled": False,
            "assign_to_roles": ["byoc"],
            "creator": config.username
        }

        resp = self.api.create_endpoint(headers=headers, data=data)
        assert 'data' in resp.json(), resp.dumps()
        assert resp.json()["data"]["endpoint_status"] == "Creating", resp.dumps()

    def test_5_create_endpoint_exists_for_comfy(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }
        data = {
            "endpoint_name": "test",
            "endpoint_type": 'Async',
            "service_type": "comfy",
            "instance_type": config.async_instance_type,
            "initial_instance_count": int(config.initial_instance_count),
            "autoscaling_enabled": False,
            "assign_to_roles": ["Designer"],
            "creator": config.username
        }

        resp = self.api.create_endpoint(headers=headers, data=data)
        assert "Cannot create already existing model" in resp.json()["message"]
