import logging
import os

import utils
from modules import scripts

auth_config_filename = 'sagemaker_auth.config'
config_path = os.path.join(scripts.basedir(), auth_config_filename)
logger = logging.getLogger(__name__)
logger.setLevel(utils.LOGGING_LEVEL)


class CloudAuthLoader:

    def __init__(self):
        if not utils.check_config_json_exist():
            self.enableAuth = False
            logger.debug('url not set')
            return

        # create an inference and upload to s3
        # Start creating model on cloud.
        self.url = utils.get_variable_from_json('api_gateway_url')
        self.api_key = utils.get_variable_from_json('api_token')
        if not self.url or not self.api_key:
            self.enableAuth = False
            logger.debug("Url or API-Key is not setting.")
            return

        self.enableAuth = True

    def enable(self):
        return self.enableAuth

    def create_config(self):
        with open(config_path, 'w+') as f:
            f.write('cyanda:password,alvindaiyan:password')

    def list_users(self):
        return []

    def clear(self):
        if os.path.isfile(config_path):
            os.remove(config_path)
