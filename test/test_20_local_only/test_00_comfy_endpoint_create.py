from __future__ import print_function

import logging
import time
from datetime import datetime
from datetime import timedelta

import config as config
from utils.api import Api

logger = logging.getLogger(__name__)


class TestComfyEndpointCreateE2E:

    def setup_class(self):
        self.api = Api(config)
        self.api.feat_oas_schema()

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
                time.sleep(5)
                if resp.status_code == 400:
                    logger.info(resp.json()['message'])
                    continue
                else:
                    break

    def test_3_create_confy_endpoint_async(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        data = {
            "endpoint_name": 'mutil-gpus',
            "service_type": "comfy",
            "endpoint_type": "Async",
            "instance_type": 'ml.g5.12xlarge',
            "initial_instance_count": 1,
            "autoscaling_enabled": False,
            "assign_to_roles": [config.role_comfy_async],
            "creator": config.username
        }

        resp = self.api.create_endpoint(headers=headers, data=data)
        assert 'data' in resp.json(), resp.dumps()
        assert resp.json()["data"]["endpoint_status"] == "Creating", resp.dumps()

    def test_1_list_endpoints_status(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        params = {
            "username": config.username
        }

        resp = self.api.list_endpoints(headers=headers, params=params)
        assert resp.status_code == 200, resp.dumps()

        endpoints = resp.json()['data']["endpoints"]
        assert len(endpoints) >= 0

        timeout = datetime.now() + timedelta(minutes=40)

        while datetime.now() < timeout:
            result = self.endpoints_wait_for_in_service()
            if result:
                break
            time.sleep(50)
        else:
            raise Exception("Create Endpoint timed out after 40 minutes.")

    def endpoints_wait_for_in_service(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        params = {
            "username": config.username
        }

        resp = self.api.list_endpoints(headers=headers, params=params)
        assert resp.status_code == 200, resp.dumps()

        for endpoint in resp.json()['data']["endpoints"]:
            endpoint_name = endpoint["endpoint_name"]

            if endpoint["endpoint_status"] == "Failed":
                raise Exception(f"{endpoint_name} is {endpoint['endpoint_status']}")
            if endpoint["endpoint_status"] != "InService":
                logger.info(f"{endpoint_name} is {endpoint['endpoint_status']}")
                return False
            else:
                return True

        return False
