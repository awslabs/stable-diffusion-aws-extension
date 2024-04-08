from __future__ import print_function

import logging

import config as config
from utils.api import Api
from utils.helper import update_oas

logger = logging.getLogger(__name__)


class TestPingApi:

    @classmethod
    def setup_class(self):
        self.api = Api(config)
        update_oas(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_1_ping_get_without_key(self):
        resp = self.api.ping()

        assert resp.status_code == 403, resp.dumps()

    def test_2_ping_with_bad_key(self):
        headers = {'x-api-key': "bad_key"}

        resp = self.api.ping(headers=headers)

        assert resp.status_code == 403, resp.dumps()

    def test_3_ping_success(self):
        headers = {'x-api-key': config.api_key}
        resp = self.api.ping(headers=headers)

        assert resp.status_code == 200, resp.dumps()
