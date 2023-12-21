import json
import logging
import os

from multi_users._types import PARTITION_KEYS, Role

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok
from lib._types import CheckPoint
from multi_users.utils import get_user_roles, check_user_permissions, get_permissions_by_username

checkpoint_table = os.environ.get('CHECKPOINT_TABLE')
bucket_name = os.environ.get('S3_BUCKET')
checkpoint_type = ["Stable-diffusion", "embeddings", "Lora", "hypernetworks", "ControlNet", "VAE"]
user_table = os.environ.get('MULTI_USER_TABLE')
CN_MODEL_EXTS = [".pt", ".pth", ".ckpt", ".safetensors", ".yaml"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ddb_service = DynamoDbUtilsService(logger=logger)
MAX_WORKERS = 10


# GET /checkpoints?username=USER_NAME&types=value&status=value
def handler(event, context):
    logger.info(json.dumps(event))
    _filter = {}

    user_roles = ['*']
    username = None
    parameters = event['queryStringParameters']
    if parameters:
        if 'types' in parameters and len(parameters['types']) > 0:
            _filter['checkpoint_type'] = parameters['types']

        if 'status' in parameters and len(parameters['status']) > 0:
            _filter['checkpoint_status'] = parameters['status']

        # todo: support multi user fetch later
        username = parameters['username'] if 'username' in parameters and parameters['username'] else None
        if username:
            user_roles = get_user_roles(ddb_service=ddb_service, user_table_name=user_table, username=username)

    requestor_name = event['requestContext']['authorizer']['username']
    requestor_permissions = get_permissions_by_username(ddb_service, user_table, requestor_name)
    requestor_created_roles_rows = ddb_service.scan(table=user_table, filters={
        'kind': PARTITION_KEYS.role,
        'creator': requestor_name
    })
    for requestor_created_roles_row in requestor_created_roles_rows:
        role = Role(**ddb_service.deserialize(requestor_created_roles_row))
        user_roles.append(role.sort_key)

    raw_ckpts = ddb_service.scan(table=checkpoint_table, filters=_filter)
    if raw_ckpts is None or len(raw_ckpts) == 0:
        data = {
            'checkpoints': []
        }
        return ok(data=data)

    ckpts = []
    for r in raw_ckpts:
        ckpt = CheckPoint(**(ddb_service.deserialize(r)))
        if check_user_permissions(ckpt.allowed_roles_or_users, user_roles, username) or (
                'user' in requestor_permissions and 'all' in requestor_permissions['user']
        ):
            ckpts.append({
                'id': ckpt.id,
                's3Location': ckpt.s3_location,
                'type': ckpt.checkpoint_type,
                'status': ckpt.checkpoint_status.value,
                'name': ckpt.checkpoint_names,
                'created': ckpt.timestamp,
                'params': ckpt.params,
                'allowed_roles_or_users': ckpt.allowed_roles_or_users
            })

    data = {
        'checkpoints': ckpts
    }

    return ok(data=data, decimal=True)
