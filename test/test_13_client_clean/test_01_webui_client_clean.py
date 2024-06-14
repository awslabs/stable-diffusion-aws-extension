import logging

import boto3

import config as config

logger = logging.getLogger(__name__)
client = boto3.client('cloudformation')

template = "https://aws-gcr-solutions.s3.amazonaws.com/extension-for-stable-diffusion-on-aws/sd.yaml"


class TestWebUiClientClean:

    @classmethod
    def setup_class(self):
        pass

    @classmethod
    def teardown_class(self):
        pass

    def test_1_delete_webui_client(self):
        response = client.delete_stack(
            StackName=config.webui_stack,
        )
        print(response)
