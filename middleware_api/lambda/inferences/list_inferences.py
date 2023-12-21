import logging
import os

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok
from common.types import InferenceJob
from common.utils import get_user_roles, check_user_permissions

inference_table_name = os.environ.get('DDB_INFERENCE_TABLE_NAME')
user_table = os.environ.get('MULTI_USER_TABLE')

logger = logging.getLogger('inference_v2')
ddb_service = DynamoDbUtilsService(logger=logger)


# GET /inferences?last_evaluated_key=xxx&limit=10&username=USER_NAME&name=SageMaker_Endpoint_Name&filter=key:value,key:value
def handler(event, ctx):
    _filter = {}

    parameters = event['queryStringParameters']

    # todo: support pagination later
    # limit = parameters['limit'] if 'limit' in parameters and parameters['limit'] else None
    # last_evaluated_key = parameters['last_evaluated_key'] if 'last_evaluated_key' in parameters and parameters[
    #     'last_evaluated_key'] else None
    #
    # if last_evaluated_key and isinstance(last_evaluated_key, str):
    #     last_evaluated_key = json.loads(last_evaluated_key)
    # last_token = None

    username = None
    if parameters:
        username = parameters['username'] if 'username' in parameters and parameters['username'] else None

    scan_rows = ddb_service.scan(inference_table_name, filters=None)
    results = []
    user_roles = []
    if username:
        user_roles = get_user_roles(ddb_service=ddb_service, user_table_name=user_table, username=username)

    for row in scan_rows:
        inference = InferenceJob(**(ddb_service.deserialize(row)))
        if username:
            if check_user_permissions(inference.owner_group_or_role, user_roles, username):
                results.append(inference.__dict__)
        else:
            results.append(inference.__dict__)

    data = {
        'inferences': results
    }

    return ok(data=data, decimal=True)
