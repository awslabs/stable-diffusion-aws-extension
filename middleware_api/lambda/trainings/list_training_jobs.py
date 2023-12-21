import logging
import os

from _types import TrainJob
from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok, bad_request
from multi_users.utils import get_permissions_by_username, get_user_roles, check_user_permissions

train_table = os.environ.get('TRAIN_TABLE')
user_table = os.environ.get('MULTI_USER_TABLE')
logger = logging.getLogger('boto3')
logger.setLevel(logging.INFO)
ddb_service = DynamoDbUtilsService(logger=logger)


# GET /trains
def handler(event, context):
    _filter = {}

    parameters = event['queryStringParameters']
    if parameters:
        if 'types' in parameters and len(parameters['types']) > 0:
            _filter['train_type'] = parameters['types']

        if 'status' in parameters and len(parameters['status']) > 0:
            _filter['job_status'] = parameters['status']

    resp = ddb_service.scan(table=train_table, filters=_filter)
    if resp is None or len(resp) == 0:
        return ok(data={'trainJobs': []})

    requestor_name = event['requestContext']['authorizer']['username']
    try:
        requestor_permissions = get_permissions_by_username(ddb_service, user_table, requestor_name)
        requestor_roles = get_user_roles(ddb_service=ddb_service, user_table_name=user_table, username=requestor_name)
        if 'train' not in requestor_permissions or \
                ('all' not in requestor_permissions['train'] and 'list' not in requestor_permissions['train']):
            return bad_request(message='user has no permission to train')

        train_jobs = []
        for tr in resp:
            train_job = TrainJob(**(ddb_service.deserialize(tr)))
            model_name = 'not_applied'
            if 'training_params' in train_job.params and 'model_name' in train_job.params['training_params']:
                model_name = train_job.params['training_params']['model_name']

            train_job_dto = {
                'id': train_job.id,
                'modelName': model_name,
                'status': train_job.job_status.value,
                'trainType': train_job.train_type,
                'created': train_job.timestamp,
                'sagemakerTrainName': train_job.sagemaker_train_name,
            }
            if train_job.allowed_roles_or_users and check_user_permissions(train_job.allowed_roles_or_users,
                                                                           requestor_roles, requestor_name):
                train_jobs.append(train_job_dto)
            elif not train_job.allowed_roles_or_users and \
                    'user' in requestor_permissions and \
                    'all' in requestor_permissions['user']:
                # superuser can view the legacy data
                train_jobs.append(train_job_dto)

        return ok(data={'trainJobs': train_jobs}, decimal=True)
    except Exception as e:
        logger.error(e)
        return bad_request(message=str(e))
