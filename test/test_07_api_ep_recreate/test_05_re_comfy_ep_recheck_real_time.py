import logging
import time
from datetime import datetime
from datetime import timedelta

import config as config
from utils.api import Api

logger = logging.getLogger(__name__)


class TestEndpointRealTimeReCheckForComfyE2E:

    def setup_class(self):
        self.api = Api(config)
        self.api.feat_oas_schema()

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

        assert config.comfy_real_time_ep_name in [endpoint["endpoint_name"] for endpoint in endpoints]

        timeout = datetime.now() + timedelta(minutes=40)

        while datetime.now() < timeout:
            result = self.endpoints_wait_for_in_service()
            if result:
                break
            time.sleep(25)
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
            if endpoint["endpoint_name"] == config.comfy_real_time_ep_name:
                if endpoint["endpoint_status"] == "InService":
                    return True

                if endpoint["endpoint_status"] == "Failed":
                    raise Exception(f"Endpoint {config.comfy_async_ep_name} is failed")

                logger.info(f"{config.comfy_async_ep_name} is {endpoint['endpoint_status']}")
                return False

        return False
