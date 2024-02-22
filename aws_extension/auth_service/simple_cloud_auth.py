import base64
import json
import logging
import os

import requests

import utils

encode_type = "utf-8"

logger = logging.getLogger(__name__)
logger.setLevel(utils.LOGGING_LEVEL)

Admin_Role = 'IT Operator'
Designer_Role = 'Designer'

def check_config_json_exist(filename='sagemaker_ui.json') -> bool:
    if os.path.exists(filename):
        with open(filename, 'r') as json_file:
            data = json.load(json_file)
            return ('api_gateway_url' in data and data['api_gateway_url']) and \
                   ('api_token' in data and data['api_token']) and \
                   ('username' in data and data['username'])

    return False


# IMPORTANT: if config changed, the class need restart to get refreshed
class CloudAuthLoader:
    username = None
    api_url = None
    api_key = None
    _auth_token = None
    _headers = None
    enableAuth = False

    def __init__(self):
        self.refresh()

    def enable(self):
        return self.enableAuth

    def update_gradio_auth(self):
        from modules import shared
        if not shared.demo:
            print('shared.demo not set yet, cannot update auth temporarily')
            return
        user_cred_str = self.create_config()
        if user_cred_str:
            for user_password in user_cred_str.split(','):
                parts = user_password.split(':')
                user = parts[0]
                password = parts[1]
                if not shared.demo.server_app.auth:
                    shared.demo.server_app.auth = {}

                shared.demo.server_app.auth[user] = password

    def create_config(self) -> str:
        return self._get_users_config_from_api()

    def _get_users_config_from_api(self):
        if not self.api_url:
            return ''
        raw_resp = requests.get(url=f'{self.api_url}users?show_password=True', headers=self._headers)
        raw_resp.raise_for_status()
        resp = raw_resp.json()['data']
        return ','.join([f"{user['username']}:{user['password']}" for user in resp['users']])

    def refresh(self):
        if not check_config_json_exist():
            self.enableAuth = False
            logger.debug('url or username not set')
            return

        # create an inference and upload to s3
        # Start creating model on cloud.
        self.api_url = utils.get_variable_from_json('api_gateway_url')
        self.api_key = utils.get_variable_from_json('api_token')

        username = utils.get_variable_from_json('username')
        self.username = username
        # password = utils.get_variable_from_json('password')
        # todo: not sure how to get current login user's password from gradio
        self._auth_token = f'Bearer {base64.b16encode(username.encode(encode_type)).decode(encode_type)}'
        self._headers = {
            'x-api-key': self.api_key,
            'Authorization': self._auth_token
        }
        self.enableAuth = True


cloud_auth_manager = CloudAuthLoader()
