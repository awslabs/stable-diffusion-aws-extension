import logging

import boto3

import config as config

logger = logging.getLogger(__name__)
client = boto3.client('cloudformation')


class TestComfyClientClean:

    @classmethod
    def setup_class(self):
        pass

    @classmethod
    def teardown_class(self):
        pass

    def test_1_delete_comfy_client(self):
        response = client.delete_stack(
            StackName=config.comfy_stack,
        )
        print(response)
