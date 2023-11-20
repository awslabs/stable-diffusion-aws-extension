import dataclasses
import os
from datetime import datetime
from unittest import TestCase

os.environ.setdefault('AWS_PROFILE', 'env')
os.environ.setdefault('S3_BUCKET', 'your-bucket')
os.environ.setdefault('DATASET_ITEM_TABLE', 'DatasetItemTable')
os.environ.setdefault('DATASET_INFO_TABLE', 'DatasetInfoTable')
os.environ.setdefault('MULTI_USER_TABLE', 'MultiUserTable')

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
        event = {
            'user_id': 'admin',
            'task_type': 'txt2img',
            'models': {
                'Stable-diffusion': ['v1-5-pruned-emaonly.safetensors'],
                'VAE': ['vae-ft-mse-840000-ema-pruned.ckpt'], 'embeddings': []
            },
            'filters': {'createAt': 1696657891.055418, 'creator': 'sd-webui'}
        }

        _id = str(datetime.now().timestamp())
        resp = prepare_inference(event, MockContext(aws_request_id=_id))
        print(resp)
        assert resp['statusCode'] == 200
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
            'user_id': 'yuxiaox',
            'task_type': 'txt2img',
            'models': {
                'Stable-diffusion': ['AnythingV5Ink_ink.safetensors'],
                'embeddings': []},
            'filters': {'createAt': 1695784940.13923, 'creator': 'sd-webui'}
        }
        _id = str(datetime.now().timestamp())
        resp = prepare_inference(event, MockContext(aws_request_id=_id))
        print(resp)
        assert resp['statusCode'] == 200
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
                'inference_id': '2f5a14ba-44c1-438a-b369-ae1102b2dcab'
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

    def test_list_all_sagemaker_endpoints(self):
        from inference_v2.sagemaker_endpoint_api import list_all_sagemaker_endpoints
        resp = list_all_sagemaker_endpoints({
            'queryStringParameters':
                {
                    'username': 'spiderman'
                },
            'x-auth': {'username': 'spiderman', 'role': ''}}, {})

        print(resp)

    def test_list_all_inference_jobs(self):
        from inference_v2.inference_api import list_all_inference_jobs
        resp = list_all_inference_jobs({
            'queryStringParameters': {
                'username': 'mickey'
            }
        }, {})

        print(resp)

    def test_generate_extra_single(self):
        self._do_generate_extra('extra-single-image', 'payload_extra_single.json')

    def test_generate_extra_batch(self):
        self._do_generate_extra('extra-batch-images', 'payload_extra_batch.json')

    def test_generate_rembg(self):
        self._do_generate_extra('rembg', 'payload_rembg.json')

    def _do_generate_extra(self, _task_type, payload_url):
        from inference_v2.inference_api import prepare_inference, run_inference

        event = {
            'user_id': 'admin',
            'task_type': _task_type,
            'models': {},
            'filters': {'createAt': datetime.now().timestamp(), 'creator': 'sd-webui'}
        }
        resp = prepare_inference(event, MockContext(aws_request_id=f'{datetime.now().timestamp()}'))
        print(resp)
        assert resp['statusCode'] == 200

        def upload_with_put(url, filename):
            with open(filename, 'rb') as file:
                import requests
                response = requests.put(url, data=file)
                response.raise_for_status()

        upload_with_put(resp['inference']['api_params_s3_upload_url'], payload_url)

        resp = run_inference({
            'pathStringParameters': {
                'inference_id': resp['inference']['id']
            }
        }, {})
        print(resp)
        assert resp['statusCode'] == 200

        print(f"result s3 location: {resp['inference']['output_path']}")


    def test_delete_endpoint(self):
        from inference_v2.sagemaker_endpoint_api import delete_sagemaker_endpoints
        resp = delete_sagemaker_endpoints({
            "delete_endpoint_list": [
                "infer-endpoint-dc-endpoint"
            ],
            "username": "admin",
        }, {})
        print(resp)
