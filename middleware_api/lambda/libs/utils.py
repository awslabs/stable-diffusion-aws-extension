import base64
import json
import logging
import os

import boto3
import time
from botocore.exceptions import ClientError

from common.ddb_service.client import DynamoDbUtilsService
from common.excepts import ForbiddenException, UnauthorizedException, NotFoundException, BadRequestException
from common.response import unauthorized, forbidden, not_found, bad_request
from libs.data_types import PARTITION_KEYS, User, Role

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

user_table = os.environ.get('MULTI_USER_TABLE')

ddb_service = DynamoDbUtilsService(logger=logger)

encode_type = "utf-8"


def log_execution_time(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.info(f"executed {func.__name__} in {(end_time - start_time) * 1000:.2f}ms")
        return result

    return wrapper


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


@log_execution_time
def check_user_existence(ddb_service, user_table, username):
    creator = ddb_service.query_items(table=user_table, key_values={
        'kind': PARTITION_KEYS.user,
        'sort_key': username,
    })

    return not creator or len(creator) == 0


@log_execution_time
def get_user_by_username(ddb_service, user_table, username):
    user_raw = ddb_service.query_items(table=user_table, key_values={
        'kind': PARTITION_KEYS.user,
        'sort_key': username,
    })

    if not user_raw or len(user_raw) == 0:
        return None

    return User(**(ddb_service.deserialize(user_raw[0])))


@log_execution_time
def get_user_roles(ddb_service, user_table_name, username):
    user = ddb_service.query_items(table=user_table_name, key_values={
        'kind': PARTITION_KEYS.user,
        'sort_key': username,
    })
    if not user or len(user) == 0:
        raise Exception(f'user: "{username}" not exist')

    user = User(**ddb_service.deserialize(user[0]))
    return user.roles


def response_error(e):
    try:
        logger.error(e, exc_info=True)
        raise e
    except UnauthorizedException as e:
        return unauthorized(message=str(e))
    except ForbiddenException as e:
        return forbidden(message=str(e))
    except NotFoundException as e:
        return not_found(message=str(e))
    except Exception as e:
        return bad_request(message=str(e))


def permissions_check(event: any, permissions: [str]):
    if 'headers' not in event:
        raise BadRequestException('Not found headers in event')

    # todo compatibility with 1.4.0, will be removed
    if 'Authorization' in event['headers']:
        authorization = event['headers']['Authorization']
        if authorization:
            username = base64.b16decode(authorization.replace('Bearer ', '').encode(encode_type)).decode(
                encode_type)
            return permissions_check_by_username(username, permissions)

    if 'username' not in event['headers']:
        raise UnauthorizedException("Unauthorized")

    return permissions_check_by_username(event['headers']['username'], permissions)


@log_execution_time
def permissions_check_by_username(username: any, permissions: [str]):
    if not username:
        raise UnauthorizedException("Unauthorized")

    user = ddb_service.query_items(table=user_table, key_values={
        'kind': PARTITION_KEYS.user,
        'sort_key': username,
    })

    if not user or len(user) == 0:
        raise UnauthorizedException("Unauthorized")

    user = User(**ddb_service.deserialize(user[0]))
    logger.info(f'user: {user}')

    roles = ddb_service.scan(table=user_table, filters={
        'kind': PARTITION_KEYS.role,
        'sort_key': user.roles,
    })

    for role_raw in roles:
        role = Role(**(ddb_service.deserialize(role_raw)))
        logger.info(f'role: {role}')
        for permission in permissions:
            if permission in role.permissions:
                return username

    return ForbiddenException(f"User {username} has no permissions: {permissions}")


def check_user_permissions(checkpoint_owners: [str], user_roles: [str], user_name: str) -> bool:
    if not checkpoint_owners or user_name in checkpoint_owners or '*' in checkpoint_owners:
        return True

    for user_role in user_roles:
        if user_role in checkpoint_owners:
            return True

    return False


@log_execution_time
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


def encode_last_key(last_evaluated_key):
    if not last_evaluated_key:
        return None
    return base64.b64encode(json.dumps(last_evaluated_key).encode(encode_type)).decode(encode_type)


def decode_last_key(last_evaluated_key):
    if not last_evaluated_key:
        return None
    return json.loads(base64.b64decode(last_evaluated_key.encode(encode_type)).decode(encode_type))
