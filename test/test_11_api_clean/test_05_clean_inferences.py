from __future__ import print_function

import logging
import time

import config as config
from utils.api import Api

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class TestCleanInferences:
    def setup_class(self):
        self.api = Api(config)
        self.api.feat_oas_schema()

    @classmethod
    def teardown_class(self):
        pass

    def test_1_clean_all_inferences(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        while True:

            resp = self.api.list_inferences(headers=headers, params={"limit": 20})
            inferences = resp.json()['data']['inferences']
            if len(inferences) == 0:
                break

            ids = []
            i = 0
            for inference in inferences:
                i = i + 1
                inference_id = inference['InferenceJobId']
                ids.append(inference_id)
                logger.info(f"delete execute {i} {inference_id}")

            data = {
                "inference_id_list": ids,
            }
            resp = self.api.delete_inferences(headers=headers, data=data)
            if resp.status_code == 400:
                logger.info(resp.json()['message'])
                time.sleep(5)
                continue
