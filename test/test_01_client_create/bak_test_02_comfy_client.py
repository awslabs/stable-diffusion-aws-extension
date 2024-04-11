import logging

import boto3
import pytest

import config as config

logger = logging.getLogger(__name__)
client = boto3.client('cloudformation')

template = "https://aws-gcr-solutions-us-east-1.s3.amazonaws.com/extension-for-stable-diffusion-on-aws/comfy.yaml"


@pytest.mark.skipif(config.is_gcr, reason="not ready in gcr")
@pytest.mark.skipif(config.test_fast, reason="test_fast")
class TestComfyClient:

    @classmethod
    def setup_class(self):
        pass

    @classmethod
    def teardown_class(self):
        pass

    def test_1_create_comfy_client_by_template(self):
        response = client.create_stack(
            StackName=config.comfy_stack,
            TemplateURL=template,
            Capabilities=['CAPABILITY_NAMED_IAM'],
            Parameters=[
                {
                    'ParameterKey': 'ApiGatewayUrl',
                    'ParameterValue': config.host_url
                },
                {
                    'ParameterKey': 'BucketName',
                    'ParameterValue': config.bucket
                },
                {
                    'ParameterKey': 'EndpointName',
                    'ParameterValue': "EndpointName"
                },
                {
                    'ParameterKey': 'ApiGatewayUrlToken',
                    'ParameterValue': config.api_key
                },
                {
                    'ParameterKey': 'InstanceType',
                    'ParameterValue': "g5.2xlarge"
                }
            ]
        )

        print(response)
