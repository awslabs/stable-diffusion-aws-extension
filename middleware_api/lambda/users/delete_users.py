import json
import logging
import os

from common.ddb_service.client import DynamoDbUtilsService
from common.response import no_content
from libs.data_types import PARTITION_KEYS
from libs.utils import KeyEncryptService
from users.create_user import _check_action_permission

user_table = os.environ.get('MULTI_USER_TABLE')
kms_key_id = os.environ.get('KEY_ID')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)

password_encryptor = KeyEncryptService()


def handler(event, ctx):
    logger.info(f'event: {event}')
    body = json.loads(event['body'])
    user_name_list = body['user_name_list']

    requestor_name = event['requestContext']['authorizer']['username']

    for username in user_name_list:
        check_permission_resp = _check_action_permission(requestor_name, username)
        if check_permission_resp:
            return check_permission_resp

        # todo: need to figure out what happens to user's resources: models, inferences, trainings and so on
        ddb_service.delete_item(user_table, keys={
            'kind': PARTITION_KEYS.user,
            'sort_key': username
        })

    return no_content(message='Users Deleted')
