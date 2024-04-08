from __future__ import print_function

import json
import logging
import os
import time
from datetime import datetime
from datetime import timedelta

import pytest
import requests

import config as config
from utils.api import Api
from utils.enums import InferenceStatus, InferenceType
from utils.helper import get_inference_job_status, update_oas

logger = logging.getLogger(__name__)
sla_batch_size = int(os.environ.get("SLA_BATCH_SIZE", 5))
inference_data = {}


class TestSLaTxt2ImgAsync:

    def setup_class(self):
        self.api = Api(config=config)
        update_oas(self.api)

    @classmethod
    def teardown_class(self):
        pass

    @pytest.mark.skipif(config.test_fast, reason="test_fast")
    def test_1_sla_txt2img(self):

        with open("./data/sla/prompts.txt", "r") as f:
            prompts = f.readlines()
            prompts = [prompt.strip() for prompt in prompts]
            prompts = [prompt for prompt in prompts if prompt != ""]
            prompts = prompts[:sla_batch_size]
            prompts_count = len(prompts)
            duration_list = []
            result_list = []
            failed_list = []
            create_infer_duration_list = []
            upload_duration_list = []
            wait_duration_list = []

            for prompt in prompts:
                result, duration, inference_id, create_infer_duration, upload_duration, wait_duration = self.sla_job(
                    prompt)
                result_list.append(result)
                if result:
                    duration_list.append(duration)
                else:
                    failed_list.append(inference_id)
                if create_infer_duration:
                    create_infer_duration_list.append(create_infer_duration)
                if upload_duration:
                    upload_duration_list.append(upload_duration)
                if wait_duration:
                    wait_duration_list.append(wait_duration)

            if len(duration_list) > 0:
                max_duration_seconds = max(duration_list)
                min_duration_seconds = min(duration_list)
                avg_duration_seconds = sum(duration_list) / len(duration_list)
            else:
                max_duration_seconds = 0
                min_duration_seconds = 0
                avg_duration_seconds = 0

            if len(create_infer_duration_list) > 0:
                create_infer_duration_avg = sum(create_infer_duration_list) / len(create_infer_duration_list)
            else:
                create_infer_duration_avg = 0

            if len(upload_duration_list) > 0:
                upload_duration_avg = sum(upload_duration_list) / len(upload_duration_list)
            else:
                upload_duration_avg = 0

            if len(wait_duration_list) > 0:
                wait_duration_avg = sum(wait_duration_list) / len(wait_duration_list)
            else:
                wait_duration_avg = 0

            if len(result_list) > 0:
                success_rate = result_list.count(True) / len(result_list)
                succeed = result_list.count(True)
                failed = result_list.count(False)
            else:
                success_rate = 0
                succeed = 0
                failed = 0

            if len(failed_list) > 0:
                failed_list_string = "failed_list:" + "\\n" + str(failed_list)
            else:
                failed_list_string = ""

            json_result = {
                "model_id": config.default_model_id,
                "instance_type": "g4/g5",
                "instance_count": int(config.initial_instance_count),
                "count": prompts_count,
                "succeed": succeed,
                "failed": failed,
                "success_rate": success_rate,
                "max_duration": max_duration_seconds,
                "min_duration": min_duration_seconds,
                "avg_duration": avg_duration_seconds,
                "failed_list": failed_list_string,
                "create_infer_duration_avg": create_infer_duration_avg,
                "upload_duration_avg": upload_duration_avg,
                "wait_duration_avg": wait_duration_avg,
            }

            with open("/tmp/txt2img_sla_report.json", "w") as sla_report:
                sla_report.write(json.dumps(json_result))

            logger.warning(json_result)

    def sla_job(self, prompt: str):
        # get start time
        start_time = datetime.now()
        result = False
        inference_id = None
        create_infer_duration = None
        upload_duration = None
        wait_duration = None
        try:
            result, inference_id, create_infer_duration, upload_duration, wait_duration = self.start_job(prompt)
        except Exception as e:
            logger.info(f"Error: {e}")

        end_time = datetime.now()

        duration = (end_time - start_time).seconds
        logger.info(f"inference_id {inference_id} result:{result} duration:{duration} prompt:{prompt}")
        return result, duration, inference_id, create_infer_duration, upload_duration, wait_duration

    def start_job(self, prompt: str):
        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        data = {
            "inference_type": "Async",
            "task_type": InferenceType.TXT2IMG.value,
            "models": {
                "Stable-diffusion": [config.default_model_id],
                "embeddings": []
            },
            "filters": {
            }
        }

        create_infer_start_time = datetime.now()
        resp = self.api.create_inference(headers=headers, data=data)
        create_infer_end_time = datetime.now()
        create_infer_duration = (create_infer_end_time - create_infer_start_time).seconds

        if 'inference' not in resp.json()['data']:
            logger.error(resp.dumps())
            return False

        inference = resp.json()['data']['inference']

        inference_id = inference["id"]

        upload_start_time = datetime.now()
        with open("./data/api_params/txt2img_api_param.json", 'rb') as data:
            data = json.load(data)
            data["prompt"] = prompt
            response = requests.put(inference["api_params_s3_upload_url"], data=json.dumps(data))
            response.raise_for_status()
        upload_end_time = datetime.now()
        upload_duration = (upload_end_time - upload_start_time).seconds

        wait_start_time = datetime.now()
        result = self.sla_txt2img_inference_job_run_and_succeed(inference_id)
        wait_end_time = datetime.now()
        wait_duration = (wait_end_time - wait_start_time).seconds

        return result, inference_id, create_infer_duration, upload_duration, wait_duration

    def sla_txt2img_inference_job_run_and_succeed(self, inference_id: str):

        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        resp = self.api.start_inference_job(job_id=inference_id, headers=headers)
        if 'statusCode' not in resp.json():
            logger.error(resp.json())
            return False

        if resp.json()['statusCode'] != 202:
            logger.error(resp.dumps())
            return False

        timeout = datetime.now() + timedelta(minutes=2)

        while datetime.now() < timeout:
            status = get_inference_job_status(
                api_instance=self.api,
                job_id=inference_id
            )
            if status == InferenceStatus.SUCCEED.value:
                return self.sla_txt2img_inference_job_image(inference_id)
            if status == InferenceStatus.FAILED.value:
                return False
            time.sleep(0.5)

        return False

    def sla_txt2img_inference_job_image(self, inference_id: str):
        global inference_data

        headers = {
            "x-api-key": config.api_key,
            "username": config.username
        }

        resp = self.api.get_inference_job(job_id=inference_id, headers=headers)
        return resp.json()['data']['status'] == 'succeed'
