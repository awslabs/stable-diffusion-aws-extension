from __future__ import print_function

import logging
import os
import uuid

import config as config
from utils.api import Api
from utils.helper import wget_file

logger = logging.getLogger(__name__)

endpoint_name = f"comfy-async-{config.endpoint_name}"

id = str(uuid.uuid4())


class TestComfyReSyncFiles:

    def setup_class(self):
        self.api = Api(config)

    @classmethod
    def teardown_class(self):
        pass

    def test_0_download_file(self):
        local_path = f"./data/comfy/checkpoints/v1-5-pruned-emaonly.ckpt"
        wget_file(
            local_path,
            'https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.ckpt'
        )

    def test_1_sync_files_to_comfy_endpoint(self):
        local = "'./data/comfy/*'"
        target = f"'s3://{config.bucket}/comfy/{endpoint_name}/{id}/models/'"
        logger.info(f"Syncing {local} to {target}")
        os.system(f"rm -rf ./s5cmd")
        os.system(f"wget -q ./ https://raw.githubusercontent.com/elonniu/s5cmd/main/s5cmd")
        os.system(f"chmod +x ./s5cmd")
        os.system(f"./s5cmd sync {local} {target}")

    def test_2_sync_files(self):
        data = {"endpoint_name": f"{endpoint_name}",
                "need_reboot": True,
                "prepare_id": id,
                "prepare_type": "models"}
        self.api.prepare(data=data)
