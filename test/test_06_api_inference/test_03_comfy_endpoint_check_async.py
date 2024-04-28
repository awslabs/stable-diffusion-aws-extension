import logging
import time
from datetime import datetime
from datetime import timedelta

import config as config
from utils.api import Api
from utils.helper import endpoints_wait_for_in_service, get_endpoint_comfy_async

logger = logging.getLogger(__name__)


class TestEndpointReCheckForComfyE2E:

    def setup_class(self):
        self.api = Api(config)
        self.api.feat_oas_schema()
        self.ep_name = get_endpoint_comfy_async(self.api)

    @classmethod
    def teardown_class(self):
        pass

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

        assert self.ep_name in [endpoint["endpoint_name"] for endpoint in endpoints]

        timeout = datetime.now() + timedelta(minutes=40)

        while datetime.now() < timeout:
            result = endpoints_wait_for_in_service(self.api, self.ep_name)
            if result:
                break
            time.sleep(5)
        else:
            raise Exception("Create Endpoint timed out after 40 minutes.")
