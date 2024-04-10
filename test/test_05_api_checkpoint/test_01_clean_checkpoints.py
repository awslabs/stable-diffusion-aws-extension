from __future__ import print_function

import logging

import config as config
from utils.api import Api
from utils.helper import update_oas

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class TestCleanCheckpoints:
    def setup_class(self):
        self.api = Api(config)
        update_oas(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_0_clean_checkpoints(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        resp = self.api.list_checkpoints(headers=headers)
        assert resp.status_code == 200, resp.dumps()
        ckpts = resp.json()['data']['checkpoints']

        id_list = []
        for ckpt in ckpts:
            if 'params' not in ckpt:
                continue
            if not ckpt['params'] or 'message' not in ckpt['params']:
                continue

            if ckpt['params']['message'] == config.ckpt_message:
                id_list.append(ckpt['id'])

        if len(id_list) == 0:
            logger.info("No checkpoints to clean")
            return

        data = {
            "checkpoint_id_list": id_list
        }

        resp = self.api.delete_checkpoints(headers=headers, data=data)
        assert resp.status_code == 204, resp.dumps()
