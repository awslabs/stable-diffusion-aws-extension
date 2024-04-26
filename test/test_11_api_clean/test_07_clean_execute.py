from __future__ import print_function

import logging
import time

import config as config
from utils.api import Api
from utils.helper import update_oas

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class TestCleanExecute:
    def setup_class(self):
        self.api = Api(config)
        update_oas(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_1_clean_all_executes(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        while True:

            resp = self.api.list_executes(headers=headers)
            executes = resp.json()['data']['executes']
            if len(executes) == 0:
                break

            for execute in executes:
                prompt_id = execute['prompt_id']
                data = {
                    "execute_id_list": [
                        prompt_id
                    ],
                }
                resp = self.api.delete_executes(headers=headers, data=data)
                logger.info(f"delete execute {prompt_id}")
                if resp.status_code == 400:
                    logger.info(resp.json()['message'])
                    time.sleep(5)
                    continue
