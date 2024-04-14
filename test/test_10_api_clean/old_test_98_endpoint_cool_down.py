from __future__ import print_function

import logging
import time
from datetime import datetime
from datetime import timedelta

import config as config
from utils.api import Api
from utils.helper import update_oas

logger = logging.getLogger(__name__)
train_job_id = ""


class TestEndpointCoolDownE2E:
    def setup_class(self):
        self.api = Api(config)
        update_oas(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_1_wait_for_endpoint_cooldown(self):

        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        resp = self.api.list_endpoints(headers=headers)
        assert resp.status_code == 200, resp.dumps()
        assert resp.json()["statusCode"] == 200

        timeout = datetime.now() + timedelta(minutes=50)

        while datetime.now() < timeout:
            result = self.train_wait_for_complete()
            if result:
                break
            time.sleep(10)
        else:
            raise Exception(f"endpoint {train_job_id} cool down timed out after 30 minutes.")

    def train_wait_for_complete(self):
        global train_job_id

        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        resp = self.api.list_endpoints(headers=headers)

        assert resp.status_code == 200, resp.dumps()

        assert 'endpoints' in resp.json()['data'], resp.dumps()

        endpoints = resp.json()['data']['endpoints']
        for endpoint in endpoints:
            if endpoint['endpoint_type'] == 'Real-time':
                continue
            if endpoint['current_instance_count'] == '0':
                return True

        return False
