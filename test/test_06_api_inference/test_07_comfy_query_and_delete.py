import json
import logging
import time
import uuid

import config as config
from utils.api import Api
from utils.helper import get_endpoint_comfy_async

logger = logging.getLogger(__name__)
prompt_id = str(uuid.uuid4())


class TestTxt2ImgReQueryAndDeleteComfyE2E:

    def setup_class(self):
        self.api = Api(config)
        self.api.feat_oas_schema()
        self.ep_name = get_endpoint_comfy_async(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_1_comfy_txt2img_async_batch_create(self):
        count = 20
        for i in range(count):
            self.comfy_txt2img_async_create()

    def comfy_txt2img_async_create(self):
        with open('./data/api_params/comfy_workflow.json', 'r') as f:
            headers = {
                "x-api-key": config.api_key,
            }
            workflow = json.load(f)
            workflow['prompt_id'] = prompt_id
            workflow['endpoint_name'] = self.ep_name
            workflow['multi_async'] = False

            resp = self.api.create_execute(headers=headers, data=workflow)
            assert resp.status_code in [200, 201], resp.dumps()
            assert resp.json()['data']['prompt_id'] == prompt_id, resp.dumps()

    def test_2_comfy_txt2img_list(self):
        last_evaluated_key = None
        while True:
            resp = self.executes_list(exclusive_start_key=last_evaluated_key)
            last_evaluated_key = resp.json()['data']['last_evaluated_key']
            logger.info(last_evaluated_key)
            if not last_evaluated_key:
                break

    def executes_list(self, exclusive_start_key=None):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        resp = self.api.list_executes(headers=headers,
                                      params={"exclusive_start_key": exclusive_start_key, "limit": 20})
        return resp

    def test_4_clean_all_executes(self):
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

    def test_5_comfy_txt2img_check_clean(self):
        resp = self.executes_list()
        assert 'data' in resp.json(), resp.dumps()
        executes = resp.json()['data']['executes']
        assert len(executes) == 0, resp.dumps()
