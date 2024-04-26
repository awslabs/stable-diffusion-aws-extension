from __future__ import print_function

import logging

import config as config
from utils.api import Api

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class TestCleanRoles:
    def setup_class(self):
        self.api = Api(config)
        self.api.feat_oas_schema()

    @classmethod
    def teardown_class(self):
        pass

    def test_1_clean_roles(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        role_name_list = []
        resp = self.api.list_roles(headers=headers)

        roles = resp.json()['data']['roles']

        for role in roles:
            if role['role_name'] == 'IT Operator':
                continue
            role_name_list.append(role['role_name'])
            logger.info(role['role_name'])

        if len(role_name_list) == 0:
            logger.info("No roles to delete")
            return

        data = {
            "role_name_list": role_name_list,
        }

        resp = self.api.delete_roles(headers=headers, data=data)
        assert resp.status_code == 204
