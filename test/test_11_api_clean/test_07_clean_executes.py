from __future__ import print_function

import logging
import time

import config as config
from utils.api import Api

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class TestCleanExecutes:
    def setup_class(self):
        self.api = Api(config)
        self.api.feat_oas_schema()

    @classmethod
    def teardown_class(self):
        pass

    def test_1_clean_all_executes(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        while True:
            resp = self.api.list_executes(headers=headers, params={"limit": 20})
            executes = resp.json()['data']['executes']
            if len(executes) == 0:
                break

            execute_id_list = []
            i = 0
            for execute in executes:
                i = i + 1
                prompt_id = execute['prompt_id']
                execute_id_list.append(prompt_id)
                logger.info(f"delete execute {i} {prompt_id}")

            data = {
                "execute_id_list": execute_id_list,
            }
            resp = self.api.delete_executes(headers=headers, data=data)
            if resp.status_code == 400:
                logger.info(resp.json()['message'])
                time.sleep(5)
                continue
