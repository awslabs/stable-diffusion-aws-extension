from __future__ import print_function

import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timedelta

import pytest

import config as config
from utils.api import Api
from utils.enums import InferenceStatus
from utils.helper import update_oas, wget_file

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

headers = {
    "x-api-key": config.api_key,
    "username": config.username
}

id = str(uuid.uuid4())


def tps_async_create(n, api, endpoint_name):
    headers = {
        "x-api-key": config.api_key,
    }

    prompt_id = str(uuid.uuid4())

    payload = json.dumps({'number': '1', 'prompt': {'3': {
        'inputs': {'seed': 156680208700286, 'steps': 20, 'cfg': 8.0, 'sampler_name': 'euler', 'scheduler': 'normal',
                   'denoise': 1.0, 'model': ['4', 0], 'positive': ['6', 0], 'negative': ['7', 0],
                   'latent_image': ['5', 0]}, 'class_type': 'KSampler', '_meta': {'title': 'KSampler'}}, '4': {
        'inputs': {'ckpt_name': 'v1-5-pruned-emaonly.ckpt'},
        'class_type': 'CheckpointLoaderSimple', '_meta': {'title': 'Load Checkpoint'}},
        '5': {'inputs': {'width': 512, 'height': 512, 'batch_size': 1},
              'class_type': 'EmptyLatentImage',
              '_meta': {'title': 'Empty Latent Image'}}, '6': {
            'inputs': {'text': 'beautiful scenery nature glass bottle landscape, , purple galaxy bottle,',
                       'clip': ['4', 1]}, 'class_type': 'CLIPTextEncode',
            '_meta': {'title': 'CLIP Text Encode (Prompt)'}},
        '7': {'inputs': {'text': 'text, watermark', 'clip': ['4', 1]},
              'class_type': 'CLIPTextEncode',
              '_meta': {'title': 'CLIP Text Encode (Prompt)'}},
        '8': {'inputs': {'samples': ['3', 0], 'vae': ['4', 2]},
              'class_type': 'VAEDecode', '_meta': {'title': 'VAE Decode'}},
        '9': {'inputs': {'filename_prefix': 'ComfyUI', 'images': ['8', 0]},
              'class_type': 'SaveImage', '_meta': {'title': 'Save Image'}}},
                          'prompt_id': prompt_id, 'extra_data': {'extra_pnginfo': {
            'workflow': {'last_node_id': 9, 'last_link_id': 9, 'nodes': [
                {'id': 7, 'type': 'CLIPTextEncode', 'pos': [413, 389],
                 'size': {'0': 425.27801513671875, '1': 180.6060791015625}, 'flags': {}, 'order': 3, 'mode': 0,
                 'inputs': [{'name': 'clip', 'type': 'CLIP', 'link': 5}],
                 'outputs': [{'name': 'CONDITIONING', 'type': 'CONDITIONING', 'links': [6], 'slot_index': 0}],
                 'properties': {'Node name for S&R': 'CLIPTextEncode'}, 'widgets_values': ['text, watermark']},
                {'id': 6, 'type': 'CLIPTextEncode', 'pos': [415, 186],
                 'size': {'0': 422.84503173828125, '1': 164.31304931640625}, 'flags': {}, 'order': 2, 'mode': 0,
                 'inputs': [{'name': 'clip', 'type': 'CLIP', 'link': 3}],
                 'outputs': [{'name': 'CONDITIONING', 'type': 'CONDITIONING', 'links': [4], 'slot_index': 0}],
                 'properties': {'Node name for S&R': 'CLIPTextEncode'},
                 'widgets_values': ['beautiful scenery nature glass bottle landscape, , purple galaxy bottle,']},
                {'id': 5, 'type': 'EmptyLatentImage', 'pos': [473, 609], 'size': {'0': 315, '1': 106}, 'flags': {},
                 'order': 0, 'mode': 0,
                 'outputs': [{'name': 'LATENT', 'type': 'LATENT', 'links': [2], 'slot_index': 0}],
                 'properties': {'Node name for S&R': 'EmptyLatentImage'}, 'widgets_values': [512, 512, 1]},
                {'id': 3, 'type': 'KSampler', 'pos': [863, 186], 'size': {'0': 315, '1': 262}, 'flags': {}, 'order': 4,
                 'mode': 0, 'inputs': [{'name': 'model', 'type': 'MODEL', 'link': 1},
                                       {'name': 'positive', 'type': 'CONDITIONING', 'link': 4},
                                       {'name': 'negative', 'type': 'CONDITIONING', 'link': 6},
                                       {'name': 'latent_image', 'type': 'LATENT', 'link': 2}],
                 'outputs': [{'name': 'LATENT', 'type': 'LATENT', 'links': [7], 'slot_index': 0}],
                 'properties': {'Node name for S&R': 'KSampler'},
                 'widgets_values': [156680208700286, 'randomize', 20, 8, 'euler', 'normal', 1]},
                {'id': 8, 'type': 'VAEDecode', 'pos': [1209, 188], 'size': {'0': 210, '1': 46}, 'flags': {}, 'order': 5,
                 'mode': 0, 'inputs': [{'name': 'samples', 'type': 'LATENT', 'link': 7},
                                       {'name': 'vae', 'type': 'VAE', 'link': 8}],
                 'outputs': [{'name': 'IMAGE', 'type': 'IMAGE', 'links': [9], 'slot_index': 0}],
                 'properties': {'Node name for S&R': 'VAEDecode'}},
                {'id': 9, 'type': 'SaveImage', 'pos': [1451, 189], 'size': {'0': 210, '1': 58}, 'flags': {}, 'order': 6,
                 'mode': 0, 'inputs': [{'name': 'images', 'type': 'IMAGE', 'link': 9}], 'properties': {},
                 'widgets_values': ['ComfyUI']},
                {'id': 4, 'type': 'CheckpointLoaderSimple', 'pos': [26, 474], 'size': {'0': 315, '1': 98}, 'flags': {},
                 'order': 1, 'mode': 0, 'outputs': [{'name': 'MODEL', 'type': 'MODEL', 'links': [1], 'slot_index': 0},
                                                    {'name': 'CLIP', 'type': 'CLIP', 'links': [3, 5], 'slot_index': 1},
                                                    {'name': 'VAE', 'type': 'VAE', 'links': [8], 'slot_index': 2}],
                 'properties': {'Node name for S&R': 'CheckpointLoaderSimple'},
                 'widgets_values': ['v1-5-pruned-emaonly.ckpt']}],
                         'links': [[1, 4, 0, 3, 0, 'MODEL'], [2, 5, 0, 3, 3, 'LATENT'], [3, 4, 1, 6, 0, 'CLIP'],
                                   [4, 6, 0, 3, 1, 'CONDITIONING'], [5, 4, 1, 7, 0, 'CLIP'],
                                   [6, 7, 0, 3, 2, 'CONDITIONING'], [7, 3, 0, 8, 0, 'LATENT'], [8, 4, 2, 8, 1, 'VAE'],
                                   [9, 8, 0, 9, 0, 'IMAGE']], 'groups': [], 'config': {}, 'extra': {}, 'version': 0.4}},
            'client_id': '6cbc8da8bb4a4012b9e40b1eae406556'},
                          'endpoint_name': endpoint_name, 'need_prepare': False, 'need_sync': False,
                          'multi_async': True})

    resp = api.create_execute(headers=headers, data=json.loads(payload))
    assert resp.status_code == 201, resp.dumps()

    inference_data = resp.json()['data']
    logger.info(f"{n} prompt_id is {prompt_id}")

    assert resp.json()["statusCode"] == 201

    prompt_id = inference_data["prompt_id"]

    timeout = datetime.now() + timedelta(minutes=5)

    while datetime.now() < timeout:
        resp = api.get_execute_job(headers=headers, prompt_id=prompt_id)
        status = resp.json()["data"]["status"]
        logger.info(f"execute {prompt_id} is {status}")
        if status == 'success':
            break
        if status == InferenceStatus.FAILED.value:
            logger.error(inference_data)
            raise Exception(f"execute {prompt_id} failed.")
        time.sleep(7)
    else:
        raise Exception(f"execute {prompt_id} timed out after 5 minutes.")


@pytest.mark.skipif(not config.is_local, reason="local test only")
class TestComfyMutilTaskGPUs:
    def setup_class(self):
        self.api = Api(config)
        self.endpoint_name = 'comfy-async-mutil-gpus'
        update_oas(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_10_download_file(self):
        local_path = f"./data/comfy/models/checkpoints/v1-5-pruned-emaonly.ckpt"
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
        logger.info(f"wait 30s for endpoint sync files...")
        time.sleep(30)

    def test_13_clean_all_executes(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        while True:

            resp = self.api.list_executes(headers=headers)
            executes = resp.json()['data']['executes']
            if len(executes) == 0:
                break

            for execute in executes:
                prompt_id = execute['prompt_id']
                data = {
                    "execute_id_list": [
                        prompt_id
                    ],
                }
                resp = self.api.delete_executes(headers=headers, data=data)
                logger.info(f"delete execute {prompt_id}")
                if resp.status_code == 400:
                    logger.info(resp.json()['message'])
                    time.sleep(5)
                    continue

    def test_14_comfy_gpus_start_async_tps(self):
        threads = []
        gpus = 1
        batch = 1
        for i in range(gpus):
            thread = threading.Thread(target=create_batch_executes, args=(batch, self.api, self.endpoint_name))
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()


def create_batch_executes(n, api, endpoint_name):
    for i in range(n):
        tps_async_create(i, api, endpoint_name)
