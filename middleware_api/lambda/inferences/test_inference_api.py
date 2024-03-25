import dataclasses
import os
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
os.environ.setdefault('INFERENCE_JOB_TABLE', 'SDInferenceJobTable')


@dataclasses.dataclass
class MockContext:
    aws_request_id: str


class InferenceApiTest(TestCase):

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

    def test_generate_extra_single(self):
        self._do_generate_extra('extra-single-image', 'payload_extra_single.json')

    def test_generate_extra_batch(self):
        self._do_generate_extra('extra-batch-images', 'payload_extra_batch.json')

    def test_generate_rembg(self):
        self._do_generate_extra('rembg', 'payload_rembg.json')

    def test_delete_endpoint(self):
        from inference_v2.sagemaker_endpoint_api import delete_sagemaker_endpoints
        resp = delete_sagemaker_endpoints({
            "delete_endpoint_list": [
                "infer-endpoint-dc-endpoint"
            ],
            "username": "admin",
        }, {})
        print(resp)
