from __future__ import print_function

import logging

import config as config
from utils.api import Api

logger = logging.getLogger(__name__)


class TestUsersApi:
    def setup_class(self):
        self.api = Api(config)
        self.api.feat_oas_schema()

    @classmethod
    def teardown_class(self):
        pass

    def test_1_list_users_without_key(self):
        resp = self.api.list_users()

        assert resp.status_code == 403, resp.dumps()

    def test_2_list_users_without_auth(self):
        headers = {"x-api-key": config.api_key}

        resp = self.api.list_users(headers=headers)

        assert resp.status_code == 401, resp.dumps()

    def test_3_list_users(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        resp = self.api.list_users(headers=headers)

        assert resp.status_code == 200, resp.dumps()

        users = resp.json()["data"]["users"]
        assert len(users) >= 0

    def test_4_delete_users_without_key(self):
        data = {
            "user_name_list": ["test"],
        }

        resp = self.api.delete_users(headers={}, data=data)

        assert resp.status_code == 403, resp.dumps()

    def test_5_delete_users_not_found(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        data = {
            "user_name_list": ["test"],
        }

        resp = self.api.delete_users(headers=headers, data=data)

        assert resp.status_code == 204, resp.dumps()

    def test_6_create_user_bad_creator(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        data = {
            "username": "XXXXXXXXXXXXX",
            "password": "XXXXXXXXXXXXX",
            "creator": "bad_creator",
            "roles": ['IT Operator'],
        }

        resp = self.api.create_user(headers=headers, data=data)

        assert resp.status_code == 201, resp.dumps()

    def test_7_create_user_with_bad_role(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        data = {
            "username": "XXXXXXXXXXXXX",
            "password": "XXXXXXXXXXXXX",
            "creator": config.username,
            "roles": ["admin"],
        }

        resp = self.api.create_user(headers=headers, data=data)

        assert resp.json()["message"] == 'user roles "admin" not exist'

    def test_8_delete_users_with_bad_params(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        data = {
        }

        resp = self.api.delete_users(headers=headers, data=data)

        assert 'object has missing required properties' in resp.json()["message"]

    def test_9_delete_users_with_username_empty(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        data = {
            "user_name_list": [""],
        }

        resp = self.api.delete_users(headers=headers, data=data)

        assert 'required minimum: 1' in resp.json()["message"]

    def test_10_create_user_api(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        data = {
            "username": config.username,
            "password": "",
            "creator": "ESD",
            "roles": ['IT Operator', 'byoc'],
        }

        resp = self.api.create_user(headers=headers, data=data)

        assert resp.status_code == 201, resp.dumps()
