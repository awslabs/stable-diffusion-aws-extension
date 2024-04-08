import logging

import boto3

import config as config
from utils.api import Api, get_schema_by_id_and_code
from utils.helper import update_oas

logger = logging.getLogger(__name__)
client = boto3.client('apigateway')


class TestApiDocExportApi:

    @classmethod
    def setup_class(self):
        self.api = Api(config)
        update_oas(self.api)

    @classmethod
    def teardown_class(self):
        pass

    def test_1_get_root(self):
        headers = {'x-api-key': config.api_key}
        resp = self.api.root(headers)
        assert resp.status_code == 200, resp.dumps

    def test_2_get_schema_by_id(self):
        operation_id = 'GetInferenceJob'
        code = 404
        get_schema_by_id_and_code(self.api, operation_id, code)
