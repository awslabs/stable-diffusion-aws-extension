import dataclasses
import os
from datetime import datetime
from unittest import TestCase

os.environ.setdefault('AWS_PROFILE', 'playground')
os.environ.setdefault('S3_BUCKET', 'stable-diffusion-aws-exten-sds3aigcbucket7db76a0b-ns8u1vc8kcce')
os.environ.setdefault('DATASET_ITEM_TABLE', 'DatasetItemTable')
os.environ.setdefault('DATASET_INFO_TABLE', 'DatasetInfoTable')
os.environ.setdefault('TRAIN_TABLE', 'TrainingTable')
os.environ.setdefault('CHECKPOINT_TABLE', 'CheckpointTable')
os.environ.setdefault('SAGEMAKER_ENDPOINT_NAME', 'aigc-utils-endpoint')

os.environ.setdefault('DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME', 'SDEndpointDeploymentJobTable')
os.environ.setdefault('DDB_INFERENCE_TABLE_NAME', 'SDInferenceJobTable')


@dataclasses.dataclass
class MockContext:
    aws_request_id: str


class InferenceApiTest(TestCase):

    def test_get_checkpoint_by_name(self):
        from inference_api import _get_checkpoint_by_name
        ckpt = _get_checkpoint_by_name('v1-5-pruned-emaonly.safetensors', 'Stable-diffusion')
        assert ckpt is not None

    def test_prepare_inference(self):
        from inference_api import prepare_inference
        event = {'sagemaker_endpoint_name': 'infer-endpoint-9958bc4', 'task_type': 'txt2img', 'models': {'Stable-diffusion': ['AnythingV5Ink_ink.safetensors'], 'ControlNet': ['control_v11p_sd15_canny.pth']}, 'filters': {'creator': 1690781890.311581}}

        _id = str(datetime.now().timestamp())
        resp = prepare_inference(event, MockContext(aws_request_id=_id))
        print(resp)
        assert resp['status'] == 200
        # get the inference job from ddb by job id

        from inference_api import inference_table_name, ddb_service
        from inference_v2._types import InferenceJob
        inference_raw = ddb_service.get_item(inference_table_name, {
            'InferenceJobId': _id
        })
        inference_job = InferenceJob(**inference_raw)
        models = {
            "space_free_size": 4e10,
            **inference_job.params['used_models'],
        }
        print(models)

        def upload_with_put(url):
            with open('api_param.json', 'rb') as file:
                import requests
                response = requests.put(url, data=file)
                response.raise_for_status()

        upload_with_put(resp['inference']['api_params_s3_upload_url'])
        from inference_api import run_inference
        resp = run_inference({
            'pathStringParameters': {
                'inference_id': _id
            }
        }, {})
        print(resp)

    def test_prepare_inference_img2img(self):
        from inference_api import prepare_inference
        event = {
            'sagemaker_endpoint_id': 'aa98c410-acdd-40fb-b927-b26935e6a777',
            'task_type': 'img2img',
            'models': {
                'Stable-diffusion': ['AnythingV5Ink_ink.safetensors'],
                'ControlNet': ['control_v11p_sd15_canny.pth', 'control_v11f1p_sd15_depth.pth']
            },
            'filters': {
                'creator': 'alvindaiyan'
            }
        }
        _id = str(datetime.now().timestamp())
        resp = prepare_inference(event, MockContext(aws_request_id=_id))
        print(resp)
        assert resp['status'] == 200
        # get the inference job from ddb by job id

        from inference_api import inference_table_name, ddb_service
        from inference_v2._types import InferenceJob
        inference_raw = ddb_service.get_item(inference_table_name, {
            'InferenceJobId': _id
        })
        inference_job = InferenceJob(**inference_raw)
        models = {
            "space_free_size": 4e10,
            **inference_job.params['used_models'],
        }
        print(models)

        def upload_with_put(url):
            with open('/Users/cyanda/Dev/python-projects/stable-diffusion-webui/extensions/stable-diffusion-aws-extension/playground_NO_COMMIT/api_img2img_param.json', 'rb') as file:
                import requests
                response = requests.put(url, data=file)
                response.raise_for_status()

        upload_with_put(resp['inference']['api_params_s3_upload_url'])
        from inference_api import run_inference
        resp = run_inference({
            'pathStringParameters': {
                'inference_id': _id
            }
        }, {})
        print(resp)

    def test_run_infer(self):
        from inference_api import run_inference
        resp = run_inference({
            'pathStringParameters': {
                'inference_id': '1690782130.721205'
            }
        }, {})
        print(resp)

    def test_upload_infer(self):
        def upload_with_put(url):
            with open('api_param.json', 'rb') as file:
                import requests
                response = requests.put(url, data=file)
                response.raise_for_status()

        s3_presigned_url = 'https://presigned_s3_url'
        upload_with_put(s3_presigned_url)

    def test_split(self):
        arg = {
            'model': 'control_v11p_sd15_canny [d14c016b]'
        }
        model_parts = arg['model'].split()
        print(' '.join(model_parts[:-1]))
