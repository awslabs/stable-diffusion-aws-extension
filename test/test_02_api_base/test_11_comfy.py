from __future__ import print_function

import logging

import config as config
from utils.api import Api
from utils.helper import update_oas

logger = logging.getLogger(__name__)


class TestComfyApiBase:
    def setup_class(self):
        self.api = Api(config)
        update_oas(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_1_create_execute_without_key(self):
        resp = self.api.create_execute()
        assert resp.status_code == 403, resp.dumps()

    def test_2_list_executes_without_key(self):
        resp = self.api.list_executes()
        assert resp.status_code == 403, resp.dumps()

    def test_3_list_executes_without_key(self):
        resp = self.api.get_execute_job(prompt_id="prompt_id")
        assert resp.status_code == 403, resp.dumps()

    def test_4_delete_executes_without_key(self):
        resp = self.api.delete_executes()
        assert resp.status_code == 403, resp.dumps()

    def test_5_create_execute_with_bad_key(self):
        headers = {'x-api-key': "bad_key"}
        resp = self.api.create_execute(headers)
        assert resp.status_code == 403, resp.dumps()

    def test_6_list_executes_with_bad_key(self):
        headers = {'x-api-key': "bad_key"}
        resp = self.api.list_executes(headers)
        assert resp.status_code == 403, resp.dumps()

    def test_7_list_executes_with_bad_key(self):
        headers = {'x-api-key': "bad_key"}
        resp = self.api.get_execute_job(headers=headers, prompt_id="prompt_id")
        assert resp.status_code == 403, resp.dumps()

    def test_8_delete_executes_with_bad_key(self):
        headers = {'x-api-key': "bad_key"}
        resp = self.api.delete_executes(headers)
        assert resp.status_code == 403, resp.dumps()
