from __future__ import print_function

import logging
import os
import uuid

import pytest

import config as config
from utils.api import Api
from utils.helper import wget_file, get_endpoint_comfy_async

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

headers = {
    "x-api-key": config.api_key,
    "username": config.username
}

id = str(uuid.uuid4())


@pytest.mark.skipif(not config.is_local, reason="local test only")
class TestComfySingleGpuDisk:
    def setup_class(self):
        self.api = Api(config)
        self.api.feat_oas_schema()
        self.endpoint_name = get_endpoint_comfy_async(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_10_download_file(self):
        local_path = f"./data/comfy/models/checkpoints/v1-5-pruned-emaonly-{config.endpoint_name}.ckpt"
        wget_file(
            local_path,
            'https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.ckpt'
        )

    def test_11_sync_files_to_comfy_endpoint(self):
        local = "'./data/comfy/models/*'"
        target = f"'s3://{config.bucket}/comfy/{self.endpoint_name}/{id}/models/'"
        logger.info(f"Syncing {local} to {target}")
        os.system(f"rm -rf ./s5cmd")
        os.system(f"wget -q ./ https://raw.githubusercontent.com/elonniu/s5cmd/main/s5cmd")
        os.system(f"chmod +x ./s5cmd")
        os.system(f"./s5cmd sync {local} {target}")

    def test_12_sync_files(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }
        data = {"endpoint_name": f"{self.endpoint_name}",
                "need_reboot": True,
                "prepare_id": id,
                "prepare_type": "models"}
        resp = self.api.prepare(data=data, headers=headers)
        assert resp.status_code == 200, resp.dumps()
        logger.info(resp.json())
