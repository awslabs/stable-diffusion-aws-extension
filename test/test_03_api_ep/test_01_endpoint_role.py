import logging

import config as config
from utils.api import Api

logger = logging.getLogger(__name__)


class TestCreateUserForComfyE2E:

    def setup_class(self):
        self.api = Api(config)
        self.api.feat_oas_schema()

    @classmethod
    def teardown_class(self):
        pass

    def test_1_create_comfy_async_role(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username,
        }

        data = {
            "role_name": config.role_comfy_async,
            "creator": "api",
            "permissions": ['train:all', 'checkpoint:all'],
        }

        self.api.create_role(headers=headers, data=data)

    def test_2_create_comfy_real_time_role(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username,
        }

        data = {
            "role_name": config.role_comfy_real_time,
            "creator": "api",
            "permissions": ['train:all', 'checkpoint:all'],
        }

        self.api.create_role(headers=headers, data=data)

    def test_3_create_sd_async_role(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username,
        }

        data = {
            "role_name": config.role_sd_async,
            "creator": "api",
            "permissions": ['train:all', 'checkpoint:all'],
        }

        self.api.create_role(headers=headers, data=data)

    def test_4_create_sd_real_time_role(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username,
        }

        data = {
            "role_name": config.role_sd_real_time,
            "creator": "api",
            "permissions": ['train:all', 'checkpoint:all'],
        }

        self.api.create_role(headers=headers, data=data)

    def test_2_update_api_roles(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username,
        }

        data = {
            "username": "api",
            "password": "admin",
            "creator": "api",
            "roles": [
                'IT Operator',
                'byoc',
                config.role_sd_real_time,
                config.role_sd_async,
                config.role_comfy_async,
                config.role_comfy_real_time,
            ],
        }

        resp = self.api.create_user(headers=headers, data=data)

        assert resp.status_code == 201, resp.dumps()
        assert resp.json()["statusCode"] == 201
