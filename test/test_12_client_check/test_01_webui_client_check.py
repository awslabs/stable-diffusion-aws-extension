import logging

import boto3
import pytest
import requests

import config

logger = logging.getLogger(__name__)
client = boto3.client('cloudformation')

template = "https://aws-gcr-solutions-us-east-1.s3.amazonaws.com/extension-for-stable-diffusion-on-aws/ec2.yaml"


@pytest.mark.skipif(config.is_gcr, reason="not ready in gcr")
@pytest.mark.skipif(config.test_fast, reason="test_fast")
@pytest.mark.skipif(config.is_local, reason="codebuild test only")
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
            stack_status = stack.get('StackStatus')
            assert stack_status in ['CREATE_COMPLETE', 'ROLLBACK_COMPLETE'], print(stack)
            outputs = stack.get('Outputs')
            if outputs:
                for output in outputs:
                    if stack_status == 'CREATE_COMPLETE':
                        url = output.get('OutputValue')
                        resp = requests.get(url)
                        assert resp.status_code == 200, print(resp.text)
