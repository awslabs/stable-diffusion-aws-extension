from __future__ import print_function

import logging
import time
from datetime import datetime
from datetime import timedelta

import pytest

import config as config
from utils.api import Api
from utils.helper import update_oas

logger = logging.getLogger(__name__)


@pytest.mark.skipif(config.is_gcr, reason="not ready in gcr")
@pytest.mark.skipif(config.test_fast, reason="test_fast")
class TestWaitTrainCompleteE2E:
    def setup_class(self):
        self.api = Api(config)
        update_oas(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_2_wait_train_wd14_job_complete(self):
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
            timeout = datetime.now() + timedelta(minutes=50)

            while datetime.now() < timeout:
                resp = self.api.get_training_job(job_id=trainJob["id"], headers=headers)
                assert resp.status_code == 200, resp.dumps()
                job_status = resp.json()["data"]['job_status']
                if job_status == "Failed" or job_status == "Fail":
                    raise Exception(f"Train is {job_status}. {resp.json()}")
                if job_status == "Completed":
                    continue
                logger.info("Train job is %s", job_status)
                time.sleep(20)
            else:
                raise Exception("Function execution timed out after 30 minutes.")
