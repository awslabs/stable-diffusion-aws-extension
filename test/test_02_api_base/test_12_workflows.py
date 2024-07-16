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

    def test_2_create_workflow_with_bad_key(self):
        headers = {'x-api-key': "bad_key"}
        resp = self.api.create_workflow(headers)
        assert resp.status_code == 403, resp.dumps()

    def test_3_create_workflow_with_bad_request(self):
        headers = {'x-api-key': config.api_key}
        resp = self.api.create_workflow(headers)
        assert resp.status_code == 400, resp.dumps()

    def test_4_list_workflows_without_key(self):
        resp = self.api.list_workflows()
        assert resp.status_code == 403, resp.dumps()

    def test_5_list_workflows_with_bad_key(self):
        headers = {'x-api-key': "bad_key"}
        resp = self.api.list_workflows(headers)
        assert resp.status_code == 403, resp.dumps()

    def test_6_list_workflows_with_ok(self):
        headers = {'x-api-key': config.api_key}
        resp = self.api.list_workflows(headers)
        assert resp.status_code == 200, resp.dumps()

    def test_7_delete_workflows_without_key(self):
        resp = self.api.delete_workflows()
        assert resp.status_code == 403, resp.dumps()

    def test_8_delete_workflows_with_bad_key(self):
        headers = {'x-api-key': "bad_key"}
        resp = self.api.delete_workflows(headers)
        assert resp.status_code == 403, resp.dumps()

    def test_9_delete_workflows_with_ok(self):
        headers = {'x-api-key': config.api_key}
        data = {
            "workflow_name_list": [
                "workflowName"
            ],
        }
        resp = self.api.delete_workflows(headers=headers, data=data)
        assert resp.status_code == 202, resp.dumps()

    def test_10_create_workflow_file_not_ready(self):
        headers = {'x-api-key': config.api_key}
        data = {
            "name": "workflow_not_ready",
            "image_uri": "uri",
            "size": "1",
            "payload_json": ""
        }
        resp = self.api.create_workflow(headers=headers, data=data)
        assert resp.status_code == 400, resp.dumps()
        assert 'files not ready' in resp.json()['message'], resp.dumps()

    def test_11_create_workflow_bad_name(self):
        headers = {'x-api-key': config.api_key}
        data = {
            "name": "workflow-bad-name",
            "image_uri": "uri",
            "size": "1",
            "payload_json": ""
        }
        resp = self.api.create_workflow(headers=headers, data=data)
        assert resp.status_code == 400, resp.dumps()
        assert 'does not match input string' in resp.json()['message'], resp.dumps()

    def test_12_get_workflow_without_key(self):
        resp = self.api.get_workflow(name='name')
        assert resp.status_code == 403, resp.dumps()

    def test_13_get_workflow_with_bad_key(self):
        headers = {'x-api-key': "bad_key"}
        resp = self.api.get_workflow(name='name', headers=headers)
        assert resp.status_code == 403, resp.dumps()

    def test_14_get_workflow_with_404(self):
        headers = {'x-api-key': config.api_key}
        resp = self.api.get_workflow(name='name', headers=headers)
        assert resp.status_code == 404, resp.dumps()
