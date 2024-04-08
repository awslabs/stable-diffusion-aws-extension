import logging

import boto3
import requests

import config

logger = logging.getLogger(__name__)
client = boto3.client('cloudformation')

template = "https://aws-gcr-solutions-us-east-1.s3.amazonaws.com/extension-for-stable-diffusion-on-aws/ec2.yaml"


class TestWebUiClientCheck:

    @classmethod
    def setup_class(self):
        pass

    @classmethod
    def teardown_class(self):
        pass

    def test_1_check_webui_client_by_template(self):
        response = client.describe_stacks(
            StackName=config.webui_stack,
        )

        stacks = response.get('Stacks')

        for stack in stacks:
            assert 'CREATE_COMPLETE' == stack.get('StackStatus'), print(stack)
            outputs = stack.get('Outputs')
            for output in outputs:
                url = output.get('OutputValue')
                resp = requests.get(url)
                assert resp.status_code == 200, print(resp.text)
