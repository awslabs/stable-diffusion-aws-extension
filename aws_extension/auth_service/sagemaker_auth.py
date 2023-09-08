import base64
import json
import logging
import os

import requests

import utils
from modules import scripts

encode_type = "utf-8"

auth_config_filename = 'sagemaker_auth.config'
config_path = os.path.join(scripts.basedir(), auth_config_filename)
logger = logging.getLogger(__name__)
logger.setLevel(utils.LOGGING_LEVEL)


def check_config_json_exist(filename='sagemaker_ui.json') -> bool:
    if os.path.exists(filename):
        with open(filename, 'r') as json_file:
            data = json.load(json_file)
            return ('api_gateway_url' in data and data['api_gateway_url']) and \
                   ('api_token' in data and data['api_token']) and \
                   ('username' in data and data['username']) and \
                   ('password' in data and data['password'])

    return False


class CloudAuthLoader:

    def __init__(self):
        if not check_config_json_exist():
            self.enableAuth = False
            logger.debug('url or username not set')
            return

        # create an inference and upload to s3
        # Start creating model on cloud.
        self.api_url = utils.get_variable_from_json('api_gateway_url')
        self.api_key = utils.get_variable_from_json('api_token')
        username = utils.get_variable_from_json('username')
        password = utils.get_variable_from_json('password')
        self._auth_token = f'Bearer {base64.b16encode((username+":"+password).encode(encode_type)).decode(encode_type)}'
        self.headers = {
            'x-api-key': self.api_key,
            'Authorization': self._auth_token
        }
        self.enableAuth = True

    def enable(self):
        return self.enableAuth

    def create_config(self) -> str:
        return self._get_users_config_from_api()

    def list_users(self, limit=10, last_evaluated_key=""):
        if not self.enableAuth:
            return {
                'users': []
            }

        raw_resp = requests.get(url=f'{self.api_url}users',
                                params={
                                    'limit': limit,
                                    'last_evaluated_key': json.dumps(last_evaluated_key)
                                },
                                headers=self.headers)
        raw_resp.raise_for_status()
        return raw_resp.json()

    def list_roles(self):
        if not self.enableAuth:
            return {
                'roles': []
            }

        raw_resp = requests.get(url=f'{self.api_url}roles', headers=self.headers)
        raw_resp.raise_for_status()
        return raw_resp.json()

    def _get_users_config_from_api(self):
        raw_resp = requests.get(url=f'{self.api_url}users?show_password=True', headers=self.headers)
        raw_resp.raise_for_status()
        resp = raw_resp.json()
        return ','.join([f"{user['username']}:{user['password']}" for user in resp['users']])

    def clear(self):
        if os.path.isfile(config_path):
            os.remove(config_path)


cloud_auth_manager = CloudAuthLoader()
