import logging

import config as config
from utils.api import Api

logger = logging.getLogger(__name__)


class TestRootApi:

    @classmethod
    def setup_class(self):
        self.api = Api(config)
        self.api.feat_oas_schema()

    @classmethod
    def teardown_class(self):
        pass

    def test_1_root_get_without_key(self):
        resp = self.api.root()
        assert resp.status_code == 403, resp.dumps()

    def test_2_root_with_bad_key(self):
        headers = {'x-api-key': "bad_key"}

        resp = self.api.root(headers=headers)
        assert resp.status_code == 403, resp.dumps()

    def test_3_get_root_succeed(self):
        headers = {'x-api-key': config.api_key}
        resp = self.api.root(headers)
        assert resp.status_code == 200, resp.dumps
