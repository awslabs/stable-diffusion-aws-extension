import dataclasses
import os
from decimal import Decimal
from unittest import TestCase

import requests

os.environ.setdefault('AWS_PROFILE', 'aws_profile')
os.environ.setdefault('S3_BUCKET', 'bucket')
os.environ.setdefault('DYNAMODB_TABLE', 'ModelTable')
os.environ.setdefault('MODEL_TABLE', 'ModelTable')
os.environ.setdefault('TRAIN_TABLE', 'TrainingTable')
os.environ.setdefault('CHECKPOINT_TABLE', 'CheckpointTable')
os.environ.setdefault('SAGEMAKER_ENDPOINT_NAME', 'aigc-utils-endpoint')
os.environ.setdefault('MULTI_USER_TABLE', 'MultiUserTable')


@dataclasses.dataclass
class MockContext:
    aws_request_id: str


class ModelsApiTest(TestCase):

    def test_upload(self):
        from models.model_api import create_model_api
        resp = create_model_api({
            "model_type": "dreambooth",
            "name": "test_upload",
            "filenames": [{
                "filename": 'test1',
                "parts_number": 5
            }],
            "params": {}
        }, MockContext(aws_request_id="asdfasdf"))
        print(resp)

        def upload_with_put(url):
            with open('test_create_model_api.py', 'rb') as file:
                response = requests.put(url, data=file)
                response.raise_for_status()

        upload_with_put(resp['s3PresignUrl'])

    def test_upload_2(self):
        url = "presign s3 url"

        def upload_with_put(url):
            with open('file.tar.gz', 'rb') as file:
                response = requests.put(url, data=file)
                response.raise_for_status()

        upload_with_put(url)

    def test_model_update(self):
        from models.model_api import update_model_job_api
        update_model_job_api({
            'model_id': 'asdfasdf',
            'status': 'Creating',
            'multi_parts_tags': {"test1": [{'ETag': '"cc95c41fa28463c8e9b88d67805f24e0"', 'PartNumber': 1}]},
        }, {})

    def test_process(self):
        data = {}  # sample data
        from models.model_api import process_result
        process_result(data, {})

    def test_convert(self):
        d = Decimal(4)
        from common.ddb_service.client import DynamoDbUtilsService
        obj = DynamoDbUtilsService._convert(d)
        print(obj)

    def test_list_all(self):
        from models.model_api import list_all_models_api
        resp = list_all_models_api({
            'queryStringParameters': {

            },
            'x-auth': {
                'username': 'admin',
                'role': ''
            }
        }, {})
        print(resp)

    def test_s3(self):
        # split s3://alvindaiyan-aigc-testing-playground/models/7a77d369-142c-4091-91e1-9278566a6a4f.out
        from models.model_api import split_s3_path
        bucket, key = split_s3_path('s3://path')
        from models.model_api import get_object
        get_object(bucket=bucket, key=key)

    def test_list_checkpoints(self):
        from model_and_train.checkpoint_api import list_all_checkpoints_api
        resp = list_all_checkpoints_api({
            'queryStringParameters': {},
            'x-auth': {
                'username': 'xman',
                'role': []
            }
        }, {})
        print(resp)

    def test_list_train_jobs(self):
        from trainings.train_api import list_all_train_jobs_api
        resp = list_all_train_jobs_api({
            'queryStringParameters': {
            },
            'x-auth': {
                'username': 'xman',
                'role': []
            }
        }, {})
        print(resp)

    def test_create_update_checkpoint(self):
        from checkpoint_api import update_checkpoint_api
        # resp = create_checkpoint_api({
        #     "checkpoint_type": "dreambooth",
        #     "filenames": [
        #         {"filename": "test1", "parts_number": 5}
        #     ],
        #     "params": {
        #         "new_model_name": "test_api",
        #         "number": 1,
        #         "string": "abc"
        #     }
        # }, MockContext(aws_request_id="asdfasdf"))
        # print(resp)
        resp = update_checkpoint_api({
            "checkpoint_id": "4e5118f5-9d9a-4a7e-aace-6f5e52c4edd9",
            "status": "Active",
            'multi_parts_tags': {"test1": [{'ETag': '"cc95c41fa28463c8e9b88d67805f24e0"', 'PartNumber': 1}]},
        }, {})
        print(resp)

    def test_update_train_job_api(self):
        from trainings.train_api import update_train_job_api
        update_train_job_api({
            "train_job_id": "asdfasdf",
            "status": "Training"
        }, {})

    def test_check_train_job_status(self):
        from trainings.train_api import check_train_job_status
        event = {'train_job_id': 'd0c19f0a-1c0f-4ac9-b7ea-6b0be8a889d0',
                 'train_job_name': 'test-new-local-2023-07-14-06-15-59-724'}
        check_train_job_status(event, {})

    def test_scan(self):
        import logging
        from common.ddb_service.client import DynamoDbUtilsService
        logger = logging.getLogger('boto3')
        ddb_service = DynamoDbUtilsService(logger=logger)
        resp = ddb_service.scan(table='ModelTable', filters={
            'model_type': 'dreambooth',
            # 'job_status': ['Initial', 'Creating', 'Complete']
        })
        print(resp)

    def test_none(self):
        import logging
        from common.ddb_service.client import DynamoDbUtilsService
        logger = logging.getLogger('boto3')
        ddb_service = DynamoDbUtilsService(logger=logger)
        ddb_service.put_items(table='ModelTable', entries={
            'id': '512d5e64-021e-49f5-a313-227f842c3f93',
            'name': 'testProgressBar01',
            'checkpoint_id': '512d5e64-021e-49f5-a313-227f842c3f93',
            'model_type': 'dreambooth',
            'job_status': 'Initial',
            'output_s3_location': 's3://placeholder.s3/dreambooth/model/testProgressBar01/512d5e64-021e-49f5-a313-227f842c3f93/output',
            'params': {'create_model_params': {'new_model_name': 'testProgressBar01',
                                               'ckpt_path': 'v1-5-pruned-emaonly.safetensors', 'from_hub': False,
                                               'new_model_url': '', 'new_model_token': '', 'extract_ema': False,
                                               'train_unfrozen': False, 'is_512': True, 'sh': None}}})
        resp = ddb_service._convert({
            'params': {'test': None}
        })
        print(resp)

    def test_multipart(self):
        import boto3
        from botocore.config import Config
        import requests
        import math
        s3 = boto3.client('s3', config=Config(signature_version='s3v4'))
        bucket = 'bucketname'
        key = 'test_multipart/tmp_10M_file'
        large_file_location = '/Users/cyanda/Dev/remote/tmp_10M_file'

        part_size = 1 * 1024 * 1024
        file_size = os.stat(large_file_location)
        print(file_size.st_size)
        parts_number = math.ceil(file_size.st_size / part_size)  # parts = 5
        print(parts_number)

        from common_tools import get_s3_multipart_signed_urls
        presign_url_resp = get_s3_multipart_signed_urls(bucket, key, parts_number)
        presign_urls = presign_url_resp['s3_signed_urls']
        upload_id = presign_url_resp['UploadId']

        with open(large_file_location, 'rb') as f:
            parts = []
            try:
                for i, signed_url in enumerate(presign_urls):
                    file_data = f.read(part_size)
                    response = requests.put(signed_url, data=file_data)
                    etag = response.headers['ETag']
                    parts.append({
                        'ETag': etag,
                        'PartNumber': i + 1
                    })

                parts.sort(key=lambda x: x['PartNumber'])
                response = s3.complete_multipart_upload(
                    Bucket=bucket,
                    Key=key,
                    MultipartUpload={'Parts': parts},
                    UploadId=upload_id
                )
                print(response)
            except Exception as e:
                print(e)
            finally:
                response = s3.abort_multipart_upload(
                    Bucket=bucket,
                    Key=key,
                    UploadId=upload_id
                )
                print(response)

    def test_batch_get_s3_multipart_signed_urls(self):
        from model_and_train.common_tools import batch_get_s3_multipart_signed_urls
        from model_and_train.types import MultipartFileReq
        resp = batch_get_s3_multipart_signed_urls(
            'bucket',
            'test-multipart-api',
            [MultipartFileReq(filename='name_not_matter', parts_number=5)]
        )
        print(resp)

    def test_list_bucket_objects(self):
        import boto3
        s3 = boto3.client('s3')
        bucket = 'alvindaiyan-aigc-testing-playground'
        key = 'Stable-diffusion/checkpoint/dytest004/8d3a46e6-756e-47a5-a138-66d66f8ffec6'
        response = s3.list_objects(
            Bucket=bucket,
            Prefix=key,
        )
        print(response)
        for obj in response['Contents']:
            print(obj['Key'].replace(f'{key}/', ""))

    def test_timestamp(self):
        import datetime
        timestamp = datetime.datetime.now().timestamp()
        print(timestamp)
        print(type(timestamp))

    def test_get_item(self):
        from models.model_api import ddb_service, model_table
        resp = ddb_service.get_item(table=model_table, key_values={
            "id": "262676e1-9b57-4ff3-a876-4e1de5ff5d25"
        })
        print(resp)

    def test_presign_urls(self):
        from common.util import get_s3_presign_urls
        bucket = 'alvindaiyan-aigc-testing-playground'
        key = 'test_upload_manual/yan'
        resp = get_s3_presign_urls(bucket_name=bucket, base_key=key, filenames=["test"])
        print(resp)

    def test_s3_download(self):
        import boto3
        s3 = boto3.client('s3')
        bucket = 'alvindaiyan-aigc-testing-playground'
        key = 'test_upload_manual/yan'
        s3.list_objects_v2()
        s3.download_file(bucket, key, 'test')
