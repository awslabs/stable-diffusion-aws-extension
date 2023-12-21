import os
from unittest import TestCase

os.environ.setdefault('AWS_PROFILE', 'playground')
os.environ.setdefault('S3_BUCKET', 'alvindaiyan-aigc-testing-playground')
os.environ.setdefault('DATASET_ITEM_TABLE', 'DatasetItemTable')
os.environ.setdefault('DATASET_INFO_TABLE', 'DatasetInfoTable')
os.environ.setdefault('TRAIN_TABLE', 'TrainingTable')
os.environ.setdefault('CHECKPOINT_TABLE', 'CheckpointTable')
os.environ.setdefault('SAGEMAKER_ENDPOINT_NAME', 'aigc-utils-endpoint')
os.environ.setdefault('MULTI_USER_TABLE', 'MultiUserTable')


class DatasetApiTest(TestCase):

    def test_create(self):
        from dataset_api import create_dataset_api
        input = {
            "dataset_name": "test_dataset",
            "content": [
                {
                    "filename": "avatar.png",
                    "name": "another_name",
                    "type": "png",
                    "params": {
                        "description": "this is uploaded for testing"
                    }
                },
                {
                    "filename": "avatar1.png",
                    "name": "another_name1",
                    "type": "png",
                    "params": {
                        "description": "this is uploaded for testing"
                    }
                },
            ],
            "params": {
                "creator": "alvindaiyan",
                "description": "test create"
            }

        }
        resp = create_dataset_api(input, {})
        print(resp['s3PresignUrl']['avatar.png'])

        def upload_with_put(url):
            with open('avatar.png', 'rb') as file:
                import requests
                response = requests.put(url, data=file)
                response.raise_for_status()

        upload_with_put(resp['s3PresignUrl']['avatar.png'])

    def test_update_dataset(self):
        from dataset_api import update_dataset_status
        input = {
            "dataset_name": "test_dataset",
            "status": "Enabled"
        }

        resp = update_dataset_status(input, {})
        print(resp)

    def test_get_dataset_item(self):
        from dataset_api import list_data_by_dataset
        resp = list_data_by_dataset({
            "pathStringParameters": {
                "dataset_name": "teesttraining"
            },
            'x-auth': {
                'username': 'xman',
                'role': []
            }
        }, {})
        print(resp)

    def test_list_datasets_api(self):
        from dataset_api import list_datasets_api
        resp = list_datasets_api({
            "queryStringParameters": {
                'dataset_status': 'Enabled'
            },
            'x-auth': {
                'username': 'xman',
                'role': []
            }
        }, {})
        print(resp)
