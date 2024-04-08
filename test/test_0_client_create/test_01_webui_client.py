import logging

import boto3

import config

logger = logging.getLogger(__name__)
client = boto3.client('cloudformation')

template = "https://aws-gcr-solutions-us-east-1.s3.amazonaws.com/extension-for-stable-diffusion-on-aws/ec2.yaml"


class TestWebUiClient:

    @classmethod
    def setup_class(self):
        pass

    @classmethod
    def teardown_class(self):
        pass

    def test_1_create_webui_client_by_template(self):
        response = client.create_stack(
            StackName=config.webui_stack,
            TemplateURL=template,
            Capabilities=['CAPABILITY_NAMED_IAM'],
            Parameters=[
                {
                    'ParameterKey': 'InstanceType',
                    'ParameterValue': 'c5.2xlarge'
                },
                {
                    'ParameterKey': 'Branch',
                    'ParameterValue': 'dev'
                }
            ]
        )

        print(response)
