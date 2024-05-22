from __future__ import print_function

import logging

import config as config
from utils.api import Api

logger = logging.getLogger(__name__)


class TestComfyWorkflowApiBase:
    def setup_class(self):
        self.api = Api(config)
        self.api.feat_oas_schema()

    @classmethod
    def teardown_class(self):
        pass

    def test_1_create_workflow_without_key(self):
        resp = self.api.create_workflow()
        assert resp.status_code == 403, resp.dumps()

    def test_2_list_workflows_without_key(self):
        resp = self.api.list_workflows()
        assert resp.status_code == 403, resp.dumps()

    def test_3_create_workflow_with_bad_key(self):
        headers = {'x-api-key': "bad_key"}
        resp = self.api.create_workflow(headers)
        assert resp.status_code == 403, resp.dumps()

    def test_4_list_workflows_with_bad_key(self):
        headers = {'x-api-key': "bad_key"}
        resp = self.api.list_workflows(headers)
        assert resp.status_code == 403, resp.dumps()

    def test_5_create_workflow_with_bad_request(self):
        headers = {'x-api-key': config.api_key}
        resp = self.api.create_workflow(headers)
        assert resp.status_code == 400, resp.dumps()

    def test_6_list_executes_with_ok(self):
        headers = {'x-api-key': config.api_key}
        resp = self.api.list_workflows(headers)
        assert resp.status_code == 200, resp.dumps()
