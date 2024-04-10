import logging

import config as config
from utils.api import Api
from utils.helper import update_oas

logger = logging.getLogger(__name__)


class TestCreateUserForComfyE2E:

    def setup_class(self):
        self.api = Api(config)
        update_oas(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_1_create_comfy_role(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username,
        }

        data = {
            "role_name": 'comfy',
            "creator": "api",
            "permissions": ['train:all', 'checkpoint:all'],
        }

        self.api.create_role(headers=headers, data=data)

    def test_2_create_user_for_comfy(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username,
        }

        data = {
            "username": "api",
            "password": "admin",
            "creator": "api",
            "roles": ['IT Operator', 'byoc', 'comfy'],
        }

        resp = self.api.create_user(headers=headers, data=data)

        assert resp.status_code == 201, resp.dumps()
        assert resp.json()["statusCode"] == 201
