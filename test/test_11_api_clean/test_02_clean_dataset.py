from __future__ import print_function

import logging

import config as config
from utils.api import Api

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class TestCleanDataset:
    def setup_class(self):
        self.api = Api(config)
        self.api.feat_oas_schema()

    @classmethod
    def teardown_class(self):
        pass

    def test_1_clean_datasets(self):
        headers = {
            "x-api-key": config.api_key
        }

        data = {
            "dataset_name_list": [
                config.dataset_name,
            ],
        }

        resp = self.api.delete_datasets(headers=headers, data=data)
        assert resp.status_code == 204
