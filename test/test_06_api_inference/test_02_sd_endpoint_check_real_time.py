from __future__ import print_function

import logging
import time
from datetime import datetime
from datetime import timedelta

import config as config
from utils.api import Api
from utils.helper import update_oas

logger = logging.getLogger(__name__)

endpoint_name = f"sd-real-time-{config.endpoint_name}"


class TestEndpointRealTimeCheckE2E:

    def setup_class(self):
        self.api = Api(config)
        update_oas(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_1_list_real_time_endpoints_status(self):
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

        assert endpoint_name in [endpoint["endpoint_name"] for endpoint in endpoints]

        timeout = datetime.now() + timedelta(minutes=40)

        while datetime.now() < timeout:
            result = self.endpoints_wait_for_in_service()
            if result:
                break
            time.sleep(15)
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
            if endpoint["endpoint_name"] == endpoint_name:
                if endpoint["endpoint_status"] == "Failed":
                    raise Exception(f"{endpoint_name} is {endpoint['endpoint_status']}")
                if endpoint["endpoint_status"] != "InService":
                    logger.info(f"{endpoint_name} is {endpoint['endpoint_status']}")
                    return False
                else:
                    return True

        return False
