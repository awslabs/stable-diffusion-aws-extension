import logging
import os
import time
import uuid

import config as config
from utils.api import Api
from utils.helper import comfy_execute_create, get_endpoint_comfy_async
from utils.helper import wget_file

logger = logging.getLogger(__name__)
prepare_id = str(uuid.uuid4())


class TestTxt2ImgInferenceAsyncAfterComfyE2E:

    def setup_class(self):
        self.api = Api(config)
        self.api.feat_oas_schema()
        self.ep_name = get_endpoint_comfy_async(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_0_download_file(self):
        local_path = f"./data/comfy/models/checkpoints/v1-5-pruned-emaonly.ckpt"
        wget_file(
            local_path,
            'https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.ckpt'
        )

    def test_1_sync_files_to_comfy_endpoint(self):
        local = "'./data/comfy/models/*'"
        target = f"'s3://{config.bucket}/comfy/{self.ep_name}/{prepare_id}/models/'"
        logger.info(f"Syncing {local} to {target}")
        os.system(f"rm -rf ./s5cmd")
        os.system(f"wget -q ./ https://raw.githubusercontent.com/elonniu/s5cmd/main/s5cmd")
        os.system(f"chmod +x ./s5cmd")
        os.system(f"./s5cmd sync {local} {target}")

    def test_2_sync_files(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }
        data = {"endpoint_name": f"{self.ep_name}",
                "need_reboot": True,
                "prepare_id": prepare_id,
                "prepare_type": "models"}
        resp = self.api.prepare(data=data, headers=headers)
        assert resp.status_code == 200, resp.dumps()
        logger.info(resp.json())
        logger.info(f"prepare {prepare_id} wait 60s for endpoint sync files...")
        time.sleep(60)

    def test_1_comfy_txt2img_async_create(self):
        comfy_execute_create(1, self.api, self.ep_name)
