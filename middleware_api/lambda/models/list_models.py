import logging
import os

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok, bad_request
from common.types import Model
from common.utils import get_permissions_by_username, get_user_roles, check_user_permissions

model_table = os.environ.get('DYNAMODB_TABLE')
user_table = os.environ.get('MULTI_USER_TABLE')

logger = logging.getLogger('boto3')
logger.setLevel(logging.INFO)
ddb_service = DynamoDbUtilsService(logger=logger)


def handler(event, context):
    _filter = {}

    parameters = event['queryStringParameters']
    if parameters:
        if 'types' in parameters and len(parameters['types']) > 0:
            _filter['model_type'] = parameters['types']

        if 'status' in parameters and len(parameters['status']) > 0:
            _filter['job_status'] = parameters['status']

    resp = ddb_service.scan(table=model_table, filters=_filter)

    if resp is None or len(resp) == 0:
        return ok(data={'models': []})

    models = []

    try:
        requestor_name = event['requestContext']['authorizer']['username']
        requestor_permissions = get_permissions_by_username(ddb_service, user_table, requestor_name)
        requestor_roles = get_user_roles(ddb_service=ddb_service, user_table_name=user_table, username=requestor_name)
        if 'train' not in requestor_permissions or \
                ('all' not in requestor_permissions['train'] and 'list' not in requestor_permissions['train']):
            return bad_request(message='user has no permission to train')

        for r in resp:
            model = Model(**(ddb_service.deserialize(r)))
            model_dto = {
                'id': model.id,
                'model_name': model.name,
                'created': model.timestamp,
                'params': model.params,
                'status': model.job_status.value,
                'output_s3_location': model.output_s3_location
            }
            if model.allowed_roles_or_users and check_user_permissions(model.allowed_roles_or_users, requestor_roles,
                                                                       requestor_name):
                models.append(model_dto)
            elif not model.allowed_roles_or_users and \
                    'user' in requestor_permissions and \
                    'all' in requestor_permissions['user']:
                # superuser can view the legacy data
                models.append(model_dto)

        return ok(data={'models': models}, decimal=True)
    except Exception as e:
        logger.error(e)
        return bad_request(message=str(e))
