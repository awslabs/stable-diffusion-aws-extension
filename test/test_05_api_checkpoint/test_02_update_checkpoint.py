from __future__ import print_function

import logging
from time import sleep

import config as config
from utils.api import Api

logger = logging.getLogger(__name__)
checkpoint_id = None
signed_urls = None


def ckpt_url():
    if config.is_gcr:
        return "https://aws-gcr-solutions.s3.cn-north-1.amazonaws.com.cn/stable-diffusion-aws-extension-github-mainline/models/cartoony.safetensors"
    return "https://huggingface.co/elonniu/esd/resolve/main/cartoony.safetensors"


class TestUpdateCheckPointE2E:

    def setup_class(self):
        self.api = Api(config)
        self.api.feat_oas_schema()

    @classmethod
    def teardown_class(self):
        pass

    def test_0_clean_checkpoints(self):
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

    def test_1_upload_lora_checkpoint_by_url(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username,
        }

        data = {
            "checkpoint_type": "Lora",
            "urls": [
                ckpt_url()
            ],
            "params": {
                "creator": config.username,
                "message": config.ckpt_message
            }
        }

        resp = self.api.create_checkpoint(headers=headers, data=data)

        assert resp.status_code == 202, resp.dumps()
        assert 'message' in resp.json()

    def test_2_checkpoint_unique_by_url(self):
        sleep(10)

        headers = {
            "x-api-key": config.api_key,
            "username": config.username,
        }

        data = {
            "checkpoint_type": "Lora",
            "urls": [
                ckpt_url()
            ],
            "params": {
                "creator": config.username,
                "message": config.ckpt_message
            }
        }

        resp = self.api.create_checkpoint(headers=headers, data=data)
        assert 'already exists' in resp.json()['message']

    def test_3_checkpoint_update_name(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username,
        }

        ckpts = self.api.list_checkpoints(headers=headers).json()['data'][
            'checkpoints']
        for ckpt in ckpts:
            if ckpt['name'][0] == 'cartoony.safetensors':
                checkpoint_id = ckpt['id']
                logger.info(f"checkpoint_id: {checkpoint_id}")
                data = {
                    "name": "cartoony"
                }
                resp = self.api.update_checkpoint(headers=headers, checkpoint_id=checkpoint_id, data=data)
                assert resp.status_code == 202, resp.dumps()

    def test_4_checkpoint_update_name_check(self):
        sleep(5)
        headers = {
            "x-api-key": config.api_key,
            "username": config.username,
        }

        rename = False
        resp = self.api.list_checkpoints(headers=headers)
        assert resp.status_code == 200, resp.dumps()

        for ckpt in resp.json()['data']['checkpoints']:
            if ckpt['name'][0] == 'cartoony':
                rename = True

        assert rename
