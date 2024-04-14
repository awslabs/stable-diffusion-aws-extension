import logging

import boto3
import pytest
import requests

import config

logger = logging.getLogger(__name__)
client = boto3.client('cloudformation')


@pytest.mark.skipif(config.is_gcr, reason="not ready in gcr")
@pytest.mark.skipif(config.test_fast, reason="test_fast")
@pytest.mark.skipif(config.is_local, reason="codebuild test only")
class TestComfyClientCheck:

    @classmethod
    def setup_class(self):
        pass

    @classmethod
    def teardown_class(self):
        pass

    def test_1_check_comfy_client_by_template(self):
        response = client.describe_stacks(
            StackName=config.comfy_stack,
        )

        stacks = response.get('Stacks')

        for stack in stacks:
            assert 'CREATE_COMPLETE' == stack.get('StackStatus'), print(stack)
            outputs = stack.get('Outputs')
            for output in outputs:
                url = output.get('OutputValue')
                resp = requests.get(url)
                assert resp.status_code == 200, print(resp.text)
