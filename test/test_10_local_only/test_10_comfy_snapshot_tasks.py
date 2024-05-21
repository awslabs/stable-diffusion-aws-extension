from __future__ import print_function

import logging
import threading
import uuid

import pytest

import config as config
from utils.api import Api
from utils.helper import comfy_execute_create, get_endpoint_comfy_async

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

headers = {
    "x-api-key": config.api_key,
    "username": config.username
}

id = str(uuid.uuid4())


@pytest.mark.skipif(not config.is_local, reason="local test only")
class TestComfySnapshotTasks:
    def setup_class(self):
        self.api = Api(config)
        self.api.feat_oas_schema()
        self.endpoint_name = get_endpoint_comfy_async(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_01_comfy_snapshot_start_async_tps(self):
        threads = []
        gpus = 1
        batch = 10000
        for i in range(gpus):
            thread = threading.Thread(target=create_batch_executes, args=(batch, self.api, self.endpoint_name))
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()


def create_batch_executes(n, api, endpoint_name):
    for i in range(n):
        comfy_execute_create(n=i, api=api, endpoint_name=endpoint_name, wait_succeed=True)
