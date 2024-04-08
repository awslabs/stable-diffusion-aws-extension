from __future__ import print_function

import logging

import config as config
from utils.api import Api
from utils.helper import update_oas

logger = logging.getLogger(__name__)


class TestDatasetsApi:
    def setup_class(self):
        self.api = Api(config)
        update_oas(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_1_list_datasets_without_key(self):
        resp = self.api.list_datasets()

        assert resp.status_code == 403, resp.dumps()

    def test_2_list_datasets_without_auth(self):
        headers = {"x-api-key": config.api_key}
        resp = self.api.list_datasets(headers=headers)

        assert resp.status_code == 401, resp.dumps()

    def test_3_list_datasets(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username,
        }

        resp = self.api.list_datasets(headers=headers)
        assert resp.status_code == 200, resp.dumps()
        assert len(resp.json()['data']["datasets"]) >= 0

    def test_4_get_dataset_missing_name(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username,
        }

        name = "not_exists"

        resp = self.api.get_dataset(headers=headers, name=name)

        assert resp.status_code == 404, resp.dumps()
        assert f"dataset {name} is not found" in resp.json()['message']

    def test_5_create_dataset_without_key(self):
        resp = self.api.create_dataset()

        assert resp.status_code == 403, resp.dumps()

    def test_6_update_dataset_without_key(self):
        resp = self.api.update_dataset(dataset_id="dataset_id")

        assert resp.status_code == 403, resp.dumps()

    def test_7_delete_datasets_without_key(self):
        headers = {}

        data = {
            "bad": ['bad'],
        }

        resp = self.api.delete_datasets(headers=headers, data=data)
        assert resp.status_code == 403, resp.dumps()

    def test_8_delete_datasets_with_bad_request_body(self):
        headers = {
            "x-api-key": config.api_key,
        }

        data = {
            "bad": ['bad'],
        }

        resp = self.api.delete_datasets(headers=headers, data=data)

        assert 'object has missing required properties' in resp.json()["message"]
        assert 'dataset_name_list' in resp.json()["message"]
