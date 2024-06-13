from __future__ import print_function

import logging

import pytest

import config as config
from utils.api import Api
from utils.helper import upload_multipart_file, wget_file

logger = logging.getLogger(__name__)
checkpoint_id = None
signed_urls = None


@pytest.mark.skipif(config.is_gcr, reason="not ready in gcr")
@pytest.mark.skipif(config.test_fast, reason="test_fast")
class TestCheckPointForTrainE2E:

    def setup_class(self):
        self.api = Api(config)
        self.api.feat_oas_schema()

    @classmethod
    def teardown_class(self):
        pass

    def test_0_clean_all_checkpoints(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username,
        }

        resp = self.api.list_checkpoints(headers=headers).json()
        checkpoints = resp['data']["checkpoints"]

        id_list = []
        for checkpoint in checkpoints:
            id_list.append(checkpoint['id'])

        if id_list:
            data = {
                "checkpoint_id_list": id_list
            }
            resp = self.api.delete_checkpoints(headers=headers, data=data)
            assert resp.status_code == 204, resp.dumps()

    def test_1_create_checkpoint_v15(self):
        filename = "v1-5-pruned-emaonly.safetensors"
        checkpoint_type = "Stable-diffusion"
        headers = {
            "x-api-key": config.api_key,
            "username": config.username,
        }

        data = {
            "checkpoint_type": checkpoint_type,
            "filenames": [
                {
                    "filename": filename,
                    "parts_number": 5
                }
            ],
            "params": {
                "message": config.ckpt_message,
                "creator": config.username
            }
        }

        resp = self.api.create_checkpoint(headers=headers, data=data)

        assert resp.status_code == 201, resp.dumps()
        assert resp.json()["statusCode"] == 201
        assert resp.json()['data']["checkpoint"]['type'] == checkpoint_type
        assert len(resp.json()['data']["checkpoint"]['id']) == 36

        global checkpoint_id
        checkpoint_id = resp.json()['data']["checkpoint"]['id']
        global signed_urls
        signed_urls = resp.json()['data']["s3PresignUrl"][filename]

    def test_3_update_checkpoint_v15(self):
        filename = "v1-5-pruned-emaonly.safetensors"
        local_path = f"/tmp/test/models/Stable-diffusion/{filename}"
        wget_file(
            local_path,
            'https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors',
            'https://aws-gcr-solutions.s3.cn-north-1.amazonaws.com.cn/stable-diffusion-aws-extension-github-mainline/models/v1-5-pruned-emaonly.safetensors'
        )
        global signed_urls
        multiparts_tags = upload_multipart_file(signed_urls, local_path)
        checkpoint_type = "Stable-diffusion"

        global checkpoint_id

        data = {
            "status": "Active",
            "multi_parts_tags": {filename: multiparts_tags}
        }

        headers = {
            "x-api-key": config.api_key,
        }

        resp = self.api.update_checkpoint(checkpoint_id=checkpoint_id, headers=headers, data=data)

        assert resp.status_code == 200, resp.dumps()
        assert resp.json()["statusCode"] == 200
        assert resp.json()['data']["checkpoint"]['type'] == checkpoint_type

    def test_4_list_checkpoints_v15_check(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username,
        }

        params = {
            "username": config.username
        }

        resp = self.api.list_checkpoints(headers=headers, params=params)
        assert resp.status_code == 200, resp.dumps()
        global checkpoint_id
        assert checkpoint_id in [checkpoint["id"] for checkpoint in resp.json()['data']["checkpoints"]]
