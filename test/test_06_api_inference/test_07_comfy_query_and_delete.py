import json
import logging
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

    def test_4_comfy_txt2img_clean(self):
        last_evaluated_key = None
        while True:
            resp = self.executes_list(exclusive_start_key=last_evaluated_key)
            executes = resp.json()['data']['executes']
            last_evaluated_key = resp.json()['data']['last_evaluated_key']

            for execute in executes:
                prompt_id = execute['prompt_id']
                headers = {
                    "x-api-key": config.api_key,
                    "username": config.username
                }
                data = {
                    "execute_id_list": [prompt_id]
                }
                resp = self.api.delete_executes(headers=headers, data=data)
                assert resp.status_code == 204, resp.dumps()
                logger.info(f"deleted prompt_id: {prompt_id}")

            if not last_evaluated_key:
                break

    def test_5_comfy_txt2img_check_clean(self):
        resp = self.executes_list()
        executes = resp.json()['data']['executes']
        assert len(executes) == 0, resp.dumps()
