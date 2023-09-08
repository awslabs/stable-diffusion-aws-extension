import json
import os
from dataclasses import dataclass
from unittest import TestCase

os.environ.setdefault('AWS_PROFILE', 'playground')
os.environ.setdefault('MULTI_USER_TABLE', 'MultiUserTable')
os_key_id = os.environ.get('TEST_KEY_ID')  # kms key id
os.environ.setdefault('KEY_ID', os_key_id)


@dataclass
class MockContext:
    aws_request_id: str


class InferenceApiTest(TestCase):

    def test_hash(self):
        json.dumps({token_zero: ""})

    def test_kms(self):
        from common.ddb_service.client import DynamoDbUtilsService
        from multi_users.utils import KeyEncryptService

        text = 'this text need to be encrypted'
        key_id = os_key_id

        key_client = KeyEncryptService()
        cipher_text = key_client.encrypt(key_id, text)
        ddb_service = DynamoDbUtilsService()
        table_name = 'MultiUserTable'
        from multi_users._types import User
        ddb_service.put_items(table_name, User(
            kind='user',
            sort_key='alvindaiyan',
            password=cipher_text,
            creator='alvindaiyan',
            roles=['IT Operator', 'Designer']
        ).__dict__)

        row = ddb_service.get_item(table_name, {
            'kind': 'user',
            'sort_key': 'alvindaiyan'
        })

        plain_txt = key_client.decrypt(key_id=key_id, cipher_text=row['password'].value)
        assert plain_txt.decode() == text

    def test_add_two_roles(self):
        from multi_users.roles_api import upsert_role
        rolenames= ['IT Operator', 'Designer']
        for rn in rolenames:
            event = {
                'role_name': rn,
                'permissions': [
                    'train:all',
                    'checkpoint:all',
                    'inference:all',
                    'sagemaker_endpoint:all',
                    'user:all'
                ],
                'creator': 'alvindaiyan'
            }
            resp = upsert_role(event, {})
            print(resp)

    def test_add_roles(self, count):
        from multi_users.roles_api import upsert_role
        event = {
            'role_name': f'RandomRole{count}',
            'permissions': [
                'train:all',
                'checkpoint:all',
                'inference:all',
                'sagemaker_endpoint:all',
                'user:all'
            ],
            'creator': 'alvindaiyan'
        }
        resp = upsert_role(event, {})
        print(resp)

    def test_batch_add_roles(self):
        for i in range(100):
            self.test_add_roles(i)

    def test_add_user(self, count):
        from multi_users.multi_users_api import upsert_user
        event = {
            'username': f'batman{count}',
            'password': 'password',
            'roles': ['IT Operator', 'Designer'],
            'creator': 'alvindaiyan'
        }
        resp = upsert_user(event, {})
        print(resp)
        assert resp['status'] == 200

    def test_batch_add_users(self):
        for i in range(300):
            self.test_add_user(i)

    def test_list_users_token(self):
        from multi_users.multi_users_api import list_user
        event = {
            'queryStringParameters': {
                # 'username': 'alvindaiyan',
                'limit': 10,
                'show_password': False,
            }
        }
        resp = list_user(event, {})
        print(len(resp['users']))
        print([u['username'] for u in resp['users']])
        print(resp['last_evaluated_key'])
        while resp['last_evaluated_key']:
            event['queryStringParameters']['last_evaluated_key'] = resp['last_evaluated_key']
            resp = list_user(event, {})
            print(len(resp['users']))
            print([u['username'] for u in resp['users']])

    def test_list_all_users(self):
        from multi_users.multi_users_api import list_user
        event = {
            'queryStringParameters': {
                'show_password': False,
            }
        }
        resp = list_user(event, {})
        print(len(resp['users']))
        print([u['username'] for u in resp['users']])


    def test_list_username(self):
        from multi_users.multi_users_api import list_user
        username = 'superman'
        event = {
            'queryStringParameters': {
                'show_password': True,
                'username': username
            }
        }
        resp = list_user(event, {})
        assert len(resp['users']) == 1
        assert [u['username'] for u in resp['users']][0] == username
        print(resp)

    def test_list_role_token(self):
        from multi_users.roles_api import list_roles
        event = {
            'queryStringParameters': {
                'limit': 10,
            }
        }
        resp = list_roles(event, {})
        print(len(resp['roles']))
        print([u['role_name'] for u in resp['roles']])
        print(resp['last_evaluated_key'])
        while resp['last_evaluated_key']:
            event['queryStringParameters']['last_evaluated_key'] = resp['last_evaluated_key']
            resp = list_roles(event, {})
            print(len(resp['roles']))
            print([u['role_name'] for u in resp['roles']])

    def test_list_all_roles(self):
        from multi_users.roles_api import list_roles
        event = {
            'queryStringParameters': {
            }
        }
        resp = list_roles(event, {})
        print(len(resp['roles']))
        print([u['role_name'] for u in resp['roles']])

    def test_list_role(self):
        from multi_users.roles_api import list_roles
        role = 'RandomRole99'
        event = {
            'queryStringParameters': {
                'role': role
            }
        }
        resp = list_roles(event, {})
        assert len(resp['roles']) == 1
        assert [r['role_name'] for r in resp['roles']][0] == role
        print(resp)

    def test_delete_user(self):
        from multi_users.multi_users_api import delete_user
        username = 'batman10'
        event = {
            'pathStringParameters': {
                'username': username
            }
        }
        resp = delete_user(event, {})
        print(resp)

        from multi_users.multi_users_api import list_user

        event = {
            'queryStringParameters': {
                'show_password': True,
                'username': username
            }
        }
        resp = list_user(event, {})
        assert len(resp['users']) == 0
