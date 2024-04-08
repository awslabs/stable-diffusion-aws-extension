from __future__ import print_function

import logging

import config as config
from utils.api import Api
from utils.helper import update_oas

logger = logging.getLogger(__name__)


class TestCheckpointsApi:

    @classmethod
    def setup_class(self):
        self.api = Api(config)
        update_oas(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_0_clean_checkpoints_api(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        resp = self.api.list_checkpoints(headers=headers)

        ckpts = resp.json()['data']['checkpoints']

        id_list = []
        for ckpt in ckpts:
            id_list.append(ckpt['id'])

        if len(id_list) == 0:
            logger.info("No checkpoints to clean")
            return

        data = {
            "checkpoint_id_list": id_list
        }

        resp = self.api.delete_checkpoints(headers=headers, data=data)

        assert resp.status_code == 204, resp.dumps()

    def test_1_list_checkpoints_without_key(self):
        resp = self.api.list_checkpoints()

        assert resp.status_code == 403, resp.dumps()

    def test_2_list_checkpoints_without_auth(self):
        headers = {"x-api-key": config.api_key}

        resp = self.api.list_checkpoints(headers=headers)

        assert resp.status_code == 401, resp.dumps()

    def test_3_list_checkpoints_without_username(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        resp = self.api.list_checkpoints(headers=headers)

        assert resp.status_code == 200, resp.dumps()

        assert resp.json()["statusCode"] == 200
        assert len(resp.json()['data']["checkpoints"]) >= 0

    def test_4_list_checkpoints_with_user_name(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        params = {"username": config.username}

        resp = self.api.list_checkpoints(headers=headers, params=params)

        assert resp.status_code == 200, resp.dumps()

        assert resp.json()["statusCode"] == 200
        assert len(resp.json()['data']["checkpoints"]) >= 0

    def test_5_create_checkpoint_with_bad_username(self):
        filename = "v1-5-pruned-emaonly.safetensors"
        checkpoint_type = "Stable-diffusion"

        headers = {
            "x-api-key": config.api_key,
            "username": config.username,
        }

        data = {
            "checkpoint_type": checkpoint_type,
            "filenames": [
                {
                    "filename": filename,
                    "parts_number": 5
                }
            ],
            "params": {
                "message": config.ckpt_message,
                "creator": "bad_username"
            }
        }

        resp = self.api.create_checkpoint(headers=headers, data=data)

        assert resp.status_code == 201, resp.dumps()

    def test_7_delete_checkpoints_with_bad_request_body(self):
        headers = {
            "x-api-key": config.api_key,
        }

        data = {
            "bad": ['bad'],
        }

        resp = self.api.delete_checkpoints(headers=headers, data=data)

        assert 'object has missing required properties' in resp.json()["message"]
        assert 'checkpoint_id_list' in resp.json()["message"]

    def test_8_delete_roles_without_key(self):
        headers = {}

        data = {
            "bad": ['bad'],
        }

        resp = self.api.delete_roles(headers=headers, data=data)
        assert resp.status_code == 403, resp.dumps()

    def test_9_update_checkpoint_without_key(self):
        resp = self.api.update_checkpoint(checkpoint_id="1111-2222-3333-4444")

        assert resp.status_code == 403, resp.dumps()
