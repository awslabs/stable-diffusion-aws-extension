from __future__ import print_function

import logging

import config as config
from utils.api import Api
from utils.helper import update_oas

logger = logging.getLogger(__name__)


class TestRolesApi:
    def setup_class(self):
        self.api = Api(config)
        update_oas(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_1_init_user_and_role(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        data = {
            "username": config.username,
            "password": config.username,
            "creator": config.username,
            "initial": True,
        }

        resp = self.api.create_user(headers=headers, data=data)

        assert resp.status_code == 201, resp.dumps()
        assert resp.json()["message"] == "Created"

    def test_2_list_roles_without_api_key(self):
        resp = self.api.list_roles()

        assert resp.status_code == 403, resp.dumps()

    def test_3_list_roles_without_auth(self):
        headers = {"x-api-key": config.api_key}
        resp = self.api.list_roles(headers=headers)

        assert resp.status_code == 401, resp.dumps()

    def test_4_create_role_without_key(self):
        resp = self.api.create_role()

        assert resp.status_code == 403, resp.dumps()

    def test_5_create_role_with_bad_creator(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        data = {
            "role_name": "role_name",
            "creator": "bad_creator",
            "permissions": ['train:all', 'checkpoint:all'],
        }

        resp = self.api.create_role(headers=headers, data=data)

        assert resp.status_code == 201, resp.dumps()

    def test_6_list_roles(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        params = {
            'role_params': 'role_name'
        }

        resp = self.api.list_roles(headers=headers, params=params)

        assert resp.status_code == 200, resp.dumps()
        roles = resp.json()['data']["roles"]
        assert len(roles) >= 1

    def test_7_list_roles_without_params(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        params = {
        }

        resp = self.api.list_roles(headers=headers, params=params)

        assert resp.status_code == 200, resp.dumps()
        roles = resp.json()['data']["roles"]
        assert len(roles) >= 1

    def test_8_delete_roles_without_key(self):
        headers = {}

        data = {
            "bad": ['bad'],
        }

        resp = self.api.delete_roles(headers=headers, data=data)

        assert resp.status_code == 403, resp.dumps()

    def test_9_delete_roles_with_bad_request_body(self):
        headers = {
            "x-api-key": config.api_key,
        }

        data = {
            "bad": ['bad'],
        }

        resp = self.api.delete_roles(headers=headers, data=data)

        assert 'object has missing required properties' in resp.json()["message"]
        assert 'role_name_list' in resp.json()["message"]

    def test_10_delete_default_role(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        data = {
            "role_name_list": ['IT Operator'],
        }

        resp = self.api.delete_roles(headers=headers, data=data)

    def test_6_create_role_byoc(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        data = {
            "role_name": "byoc",
            "creator": "ESD",
            "permissions": [
                'train:all',
                'checkpoint:all',
                'inference:all',
                'sagemaker_endpoint:all',
                'user:all',
                'role:all',
            ],
        }

        resp = self.api.create_role(headers=headers, data=data)

        assert resp.status_code == 201, resp.dumps()
