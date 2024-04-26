from __future__ import print_function

import logging

import config as config
from utils.api import Api

logger = logging.getLogger(__name__)


class TestComfyApiBase:
    def setup_class(self):
        self.api = Api(config)
        self.api.feat_oas_schema()

    @classmethod
    def teardown_class(self):
        pass

    def test_1_create_execute_without_key(self):
        resp = self.api.create_execute()
        assert resp.status_code == 403, resp.dumps()

    def test_2_list_executes_without_key(self):
        resp = self.api.list_executes()
        assert resp.status_code == 403, resp.dumps()

    def test_3_get_execute_job_without_key(self):
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

    def test_7_get_execute_job_with_bad_key(self):
        headers = {'x-api-key': "bad_key"}
        resp = self.api.get_execute_job(headers=headers, prompt_id="prompt_id")
        assert resp.status_code == 403, resp.dumps()

    def test_8_delete_executes_with_bad_key(self):
        headers = {'x-api-key': "bad_key"}
        resp = self.api.delete_executes(headers)
        assert resp.status_code == 403, resp.dumps()

    def test_9_create_execute_with_bad_request(self):
        headers = {'x-api-key': config.api_key}
        resp = self.api.create_execute(headers)
        assert resp.status_code == 400, resp.dumps()

    def test_10_list_executes_with_ok(self):
        headers = {'x-api-key': config.api_key}
        resp = self.api.list_executes(headers)
        assert resp.status_code == 200, resp.dumps()

    def test_11_get_execute_job_with_404(self):
        headers = {'x-api-key': config.api_key}
        resp = self.api.get_execute_job(headers=headers, prompt_id="prompt_id")
        assert resp.status_code == 404, resp.dumps()

    def test_12_delete_executes_with_bad_request(self):
        headers = {'x-api-key': config.api_key}
        resp = self.api.delete_executes(headers)
        assert resp.status_code == 400, resp.dumps()
