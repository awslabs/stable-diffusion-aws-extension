import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

from libs.data_types import PARTITION_KEYS, User, Role


logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

class KeyEncryptService:

    def __init__(self, logging_level=logging.INFO):
        self.kms_client = boto3.client('kms')
        self.logger = logging.getLogger('boto3')
        self.logger.setLevel(logging_level)

    def encrypt(self, key_id: str, text: str) -> bytes:
        """
        Encrypts text by using the specified key.

        :param key_id: The ARN or ID of the key to use for encryption.
        :param text: The text need to be encrypted
        :return: The encrypted version of the text.
        """
        try:
            cipher_text = self.kms_client.encrypt(
                KeyId=key_id, Plaintext=text.encode())['CiphertextBlob']
        except ClientError as err:
            self.logger.error(
                "Couldn't encrypt text. Here's why: %s", err.response['Error']['Message'])
        else:
            self.logger.debug(f"Your ciphertext is: {cipher_text}")
            return cipher_text

    def decrypt(self, key_id: str, cipher_text: bytes) -> bytes:
        """
        Decrypts text previously encrypted with a key.

        :param key_id: The ARN or ID of the key used to decrypt the data.
        :param cipher_text: The encrypted text to decrypt.
        """
        try:
            text = self.kms_client.decrypt(KeyId=key_id, CiphertextBlob=cipher_text)['Plaintext']
        except ClientError as err:
            self.logger.error("Couldn't decrypt your ciphertext. Here's why: %s",
                              err.response['Error']['Message'])

        else:
            self.logger.debug(f"Your plaintext is {text.decode()}")
            return text


def check_user_existence(ddb_service, user_table, username):
    creator = ddb_service.query_items(table=user_table, key_values={
        'kind': PARTITION_KEYS.user,
        'sort_key': username,
    })

    return not creator or len(creator) == 0


def get_user_by_username(ddb_service, user_table, username):
    user_raw = ddb_service.query_items(table=user_table, key_values={
        'kind': PARTITION_KEYS.user,
        'sort_key': username,
    })

    if not user_raw or len(user_raw) == 0:
        return None

    return User(**(ddb_service.deserialize(user_raw[0])))


def get_user_roles(ddb_service, user_table_name, username):
    user = ddb_service.query_items(table=user_table_name, key_values={
        'kind': PARTITION_KEYS.user,
        'sort_key': username,
    })
    if not user or len(user) == 0:
        raise Exception(f'user: "{username}" not exist')

    user = User(**ddb_service.deserialize(user[0]))
    return user.roles


def check_user_permissions(checkpoint_owners: [str], user_roles: [str], user_name: str) -> bool:
    if not checkpoint_owners or user_name in checkpoint_owners or '*' in checkpoint_owners:
        return True

    for user_role in user_roles:
        if user_role in checkpoint_owners:
            return True

    return False


def get_permissions_by_username(ddb_service, user_table, username):
    creator_roles = get_user_roles(ddb_service, user_table, username)
    roles = ddb_service.scan(table=user_table, filters={
        'kind': PARTITION_KEYS.role,
        'sort_key': creator_roles,
    })
    permissions = {}
    for role_raw in roles:
        role = Role(**(ddb_service.deserialize(role_raw)))
        for permission in role.permissions:
            permission_parts = permission.split(':')
            resource = permission_parts[0]
            action = permission_parts[1]

            if resource not in permissions:
                permissions[resource] = set()

            permissions[resource].add(action)

    return permissions


# for cloudwatch visualization
def log_json(json_obj, title: str = None, level=logging.INFO):
    if title is None:
        logger.log(level, title)
    logger.log(level, json.dumps(json_obj, indent=2, default=str))
