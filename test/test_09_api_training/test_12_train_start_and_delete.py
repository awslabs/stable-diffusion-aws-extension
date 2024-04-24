from __future__ import print_function

import logging
import time

import pytest

import config as config
from utils.api import Api
from utils.helper import update_oas

logger = logging.getLogger(__name__)


@pytest.mark.skipif(config.is_gcr, reason="not ready in gcr")
@pytest.mark.skipif(config.test_fast, reason="test_fast")
class TestTrainStartDeleteE2E:
    def setup_class(self):
        self.api = Api(config)
        update_oas(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_0_clear_all_trains(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        resp = self.api.list_trainings(headers=headers)

        assert resp.status_code == 200, resp.dumps()
        assert resp.json()["statusCode"] == 200
        assert 'trainings' in resp.json()["data"]
        trainJobs = resp.json()["data"]["trainings"]
        for trainJob in trainJobs:
            data = {
                "training_id_list": [trainJob["id"]],
            }
            resp = self.api.delete_trainings(data=data, headers=headers)
            assert resp.status_code == 204, resp.dumps()

    def test_1_train_job_create(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        payload = {
            "lora_train_type": "kohya",
            "params": {
                "training_params": {
                    "training_instance_type": config.train_instance_type,
                    "model": config.default_model_id,
                    "dataset": config.dataset_name,
                    "fm_type": "sd_1_5"
                },
                "config_params": {
                    "output_name": 'new_train_model_name',
                    "save_every_n_epochs": 1,
                    "max_train_epochs": 1
                }
            }
        }

        resp = self.api.create_training_job(headers=headers, data=payload)
        time.sleep(40)
        assert resp.status_code == 201, resp.dumps()

    def test_2_delete_all_trains_jobs(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        resp = self.api.list_trainings(headers=headers)

        assert resp.status_code == 200, resp.dumps()
        assert resp.json()["statusCode"] == 200
        assert 'trainings' in resp.json()["data"]
        train_jobs = resp.json()["data"]["trainings"]
        assert len(train_jobs) > 0
        for trainJob in train_jobs:
            data = {
                "training_id_list": [trainJob["id"]],
            }
            resp = self.api.delete_trainings(data=data, headers=headers)
            assert resp.status_code == 204, resp.dumps()

    def test_3_train_job_create_for_name_check(self):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        payload = {
            "lora_train_type": "kohya",
            "params": {
                "training_params": {
                    "training_instance_type": config.train_instance_type,
                    "model": config.default_model_id,
                    "dataset": config.dataset_name,
                    "fm_type": "sd_1_5"
                },
                "config_params": {
                    "output_name": config.train_wd14_model_name,
                    "save_every_n_epochs": 1,
                    "max_train_epochs": 1
                }
            }
        }

        resp = self.api.create_training_job(headers=headers, data=payload)
        assert config.train_wd14_model_name in resp.json()["message"], resp.dumps()
