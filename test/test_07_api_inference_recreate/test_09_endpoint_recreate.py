from __future__ import print_function

import logging
from time import sleep

import config as config
from utils.api import Api
from utils.helper import update_oas

logger = logging.getLogger(__name__)


class TestEndpointReCreateE2E:

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

    def test_2_create_endpoint_async(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        data = {
            "endpoint_name": config.endpoint_name,
            "endpoint_type": "Async",
            "instance_type": config.async_instance_type,
            "initial_instance_count": 1,
            "autoscaling_enabled": True,
            "assign_to_roles": ["IT Operator"],
            "creator": config.username
        }

        resp = self.api.create_endpoint(headers=headers, data=data)
        assert 'data' in resp.json(), resp.dumps()
        assert resp.json()["data"]["endpoint_status"] == "Creating", resp.dumps()

    def test_3_create_endpoint_real_time(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        data = {
            "endpoint_name": config.endpoint_name,
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
