from __future__ import print_function

import logging
import time

import config as config
from utils.api import Api
from utils.helper import get_endpoint_status, delete_sagemaker_endpoint, update_oas

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class TestCleanEndpoint:
    def setup_class(self):
        self.api = Api(config)
        update_oas(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_1_delete_endpoints_async(self):
        endpoint_name = f"sd-async-{config.endpoint_name}"
        while True:
            status = get_endpoint_status(self.api, endpoint_name)
            if status is None:
                break

            if status in ['Creating', 'Updating']:
                logger.warning(f"Endpoint {endpoint_name} is {status}, waiting to delete...")
                time.sleep(10)
            else:
                delete_sagemaker_endpoint(self.api, endpoint_name)
                break
        pass

    def test_2_delete_endpoints_real_time(self):
        endpoint_name = f"sd-real-time-{config.endpoint_name}"
        while True:
            status = get_endpoint_status(self.api, endpoint_name)
            if status is None:
                break

            if status in ['Creating', 'Updating']:
                logger.warning(f"Endpoint {endpoint_name} is {status}, waiting to delete...")
                time.sleep(10)
            else:
                delete_sagemaker_endpoint(self.api, endpoint_name)
                break
        pass

    def test_3_delete_endpoints_async_comfy(self):
        while True:
            status = get_endpoint_status(self.api, config.comfy_async_ep_name)
            if status is None:
                break

            if status in ['Creating', 'Updating']:
                logger.warning(f"Endpoint {config.comfy_async_ep_name} is {status}, waiting to delete...")
                time.sleep(10)
            else:
                delete_sagemaker_endpoint(self.api, config.comfy_async_ep_name)
                break
        pass

    def test_4_delete_endpoints_real_time_comfy(self):
        while True:
            status = get_endpoint_status(self.api, config.comfy_real_time_ep_name)
            if status is None:
                break

            if status in ['Creating', 'Updating']:
                logger.warning(f"Endpoint {config.comfy_real_time_ep_name} is {status}, waiting to delete...")
                time.sleep(10)
            else:
                delete_sagemaker_endpoint(self.api, config.comfy_real_time_ep_name)
                break
        pass

    def test_5_clean_all_endpoints(self):
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
                    time.sleep(5)
                    continue
                else:
                    break
