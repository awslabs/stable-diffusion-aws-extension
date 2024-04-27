import json
import logging
import time
import uuid

import config as config
from utils.api import Api
from utils.helper import get_endpoint_comfy_async

logger = logging.getLogger(__name__)

prompt_id = str(uuid.uuid4())


class TestReTxt2ImgReCreateAndGetComfyE2E:

    def setup_class(self):
        self.api = Api(config)
        self.api.feat_oas_schema()
        self.ep_name = get_endpoint_comfy_async(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_0_comfy_txt2img_async_create(self):
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

    def test_2_comfy_txt2img_get(self):
        headers = {
            "x-api-key": config.api_key,
        }
        time.sleep(15)
        self.api.get_execute_job(headers=headers, prompt_id=prompt_id)
