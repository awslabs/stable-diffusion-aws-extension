import logging

import boto3

logger = logging.getLogger(__name__)
client = boto3.client('apigateway')

template = "https://aws-gcr-solutions-us-east-1.s3.amazonaws.com/extension-for-stable-diffusion-on-aws/ec2.yaml"


class TestWebUiClient:

    @classmethod
    def setup_class(self):
        pass

    @classmethod
    def teardown_class(self):
        pass

    def test_1_create_webui_by_template(self):
        print(template)
