from __future__ import print_function

import logging

import config as config
from utils.api import Api

logger = logging.getLogger(__name__)


class TestComfySchemasApiBase:
    def setup_class(self):
        self.api = Api(config)
        self.api.feat_oas_schema()

    @classmethod
    def teardown_class(self):
        pass

    def test_1_create_schema_without_key(self):
        resp = self.api.create_schema()
        assert resp.status_code == 403, resp.dumps()

    def test_2_create_schema_with_bad_key(self):
        headers = {'x-api-key': "bad_key"}
        resp = self.api.create_schema(headers)
        assert resp.status_code == 403, resp.dumps()

    def test_3_create_schema_with_bad_request(self):
        headers = {'x-api-key': config.api_key}
        resp = self.api.create_schema(headers)
        assert resp.status_code == 400, resp.dumps()

    def test_4_list_schemas_without_key(self):
        resp = self.api.list_schemas()
        assert resp.status_code == 403, resp.dumps()

    def test_5_list_schemas_with_bad_key(self):
        headers = {'x-api-key': "bad_key"}
        resp = self.api.list_schemas(headers)
        assert resp.status_code == 403, resp.dumps()

    def test_6_list_schemas_with_ok(self):
        headers = {'x-api-key': config.api_key}
        resp = self.api.list_schemas(headers)
        assert resp.status_code == 200, resp.dumps()

    def test_7_delete_schemas_without_key(self):
        resp = self.api.delete_schemas()
        assert resp.status_code == 403, resp.dumps()

    def test_8_delete_schemas_with_bad_key(self):
        headers = {'x-api-key': "bad_key"}
        resp = self.api.delete_schemas(headers)
        assert resp.status_code == 403, resp.dumps()

    def test_9_delete_schemas_with_ok(self):
        headers = {'x-api-key': config.api_key}
        data = {
            "schema_name_list": [
                "name"
            ],
        }
        resp = self.api.delete_schemas(headers=headers, data=data)
        assert resp.status_code == 204, resp.dumps()

    def test_10_create_schema_without_name(self):
        headers = {'x-api-key': config.api_key}
        data = {
            "name1": "",
        }
        resp = self.api.create_schema(headers=headers, data=data)
        assert resp.status_code == 400, resp.dumps()
        assert 'has missing required properties' in resp.json()['message'], resp.dumps()
