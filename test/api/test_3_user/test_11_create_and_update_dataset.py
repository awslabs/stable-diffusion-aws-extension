from __future__ import print_function

import logging
import os

import requests

import config as config
from utils.api import Api
from utils.helper import update_oas

logger = logging.getLogger(__name__)
dataset = {}


class TestDatasetE2E:
    def setup_class(self):
        self.api = Api(config)
        update_oas(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_0_clear_all_datasets(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username,
        }

        resp = self.api.list_datasets(headers=headers)
        assert resp.status_code == 200, resp.dumps()
        assert 'datasets' in resp.json()['data'], resp.dumps()
        datasets = resp.json()['data']['datasets']
        for dataset in datasets:
            data = {
                "dataset_name_list": [
                    dataset['datasetName'],
                ],
            }
            resp = self.api.delete_datasets(data=data, headers=headers)
            assert resp.status_code == 204, resp.dumps()

    def test_1_dataset_post(self):
        dataset_content = []

        for filename in os.listdir("./data/dataset"):
            dataset_content.append({
                'filename': filename,
                'name': filename,
                'type': 'image',
                'params': {}
            })

        headers = {
            "x-api-key": config.api_key,
            "username": config.username,
        }

        data = {
            'dataset_name': config.dataset_name,
            'content': dataset_content,
            'creator': config.username,
            'prefix': '10_technic',
            'params': {'description': 'this is description'}
        }

        resp = self.api.create_dataset(headers=headers, data=data)
        assert resp.status_code == 201, resp.dumps()

        global dataset
        dataset = resp.json()

        assert resp.json()["statusCode"] == 201
        assert resp.json()['data']["datasetName"] == config.dataset_name

    def test_2_dataset_img_upload(self):
        global dataset
        for filename, presign_url in dataset['data']['s3PresignUrl'].items():
            file_path = f"./data/dataset/{filename}"
            with open(file_path, 'rb') as file:
                resp = requests.put(presign_url, file)
                resp.raise_for_status()
                assert resp.status_code == 200

    def test_3_dataset_update_status(self):
        global dataset
        headers = {
            "x-api-key": config.api_key,
            "username": config.username,
        }

        data = {
            "status": "Enabled"
        }

        resp = self.api.update_dataset(dataset_id=config.dataset_name, headers=headers, data=data)
        assert resp.status_code == 200, resp.dumps()

        assert resp.json()["statusCode"] == 200

    def test_4_datasets_get(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username,
        }

        resp = self.api.list_datasets(headers=headers)
        assert resp.status_code == 200, resp.dumps()

        datasets = resp.json()['data']["datasets"]

        assert config.dataset_name in [user["datasetName"] for user in datasets]

    def test_5_dataset_get(self):
        dataset_name = config.dataset_name

        headers = {
            "x-api-key": config.api_key,
            "username": config.username,
        }

        resp = self.api.get_dataset(name=dataset_name, headers=headers)
        assert resp.status_code == 200, resp.dumps()

        assert resp.json()["statusCode"] == 200
