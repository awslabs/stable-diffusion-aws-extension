import json
import logging
import os

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok, bad_request
from common.schemas.trainings import TrainingCollection, TrainingLink, TrainingItem
from common.util import get_multi_query_params, generate_url
from libs.data_types import TrainJob
from libs.utils import get_permissions_by_username, get_user_roles, check_user_permissions

train_table = os.environ.get('TRAIN_TABLE')
user_table = os.environ.get('MULTI_USER_TABLE')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)


# GET /trains
def handler(event, context):
    logger.info(json.dumps(event))

    _filter = {}

    training_collection = TrainingCollection(
        items=[],
        links=[
            TrainingLink(href=generate_url(event, f'trainings'), rel="self", type="GET"),
            TrainingLink(href=generate_url(event, f'trainings'), rel="create", type="POST"),
            TrainingLink(href=generate_url(event, f'trainings'), rel="delete", type="DELETE"),
        ]
    )

    types = get_multi_query_params(event, 'types')
    if types:
        _filter['train_type'] = types

    status = get_multi_query_params(event, 'status')
    if status:
        _filter['job_status'] = status

    resp = ddb_service.scan(table=train_table, filters=_filter)
    if resp is None or len(resp) == 0:
        return ok(data=training_collection.dict(), decimal=True)

    requestor_name = event['requestContext']['authorizer']['username']
    try:
        requestor_permissions = get_permissions_by_username(ddb_service, user_table, requestor_name)
        requestor_roles = get_user_roles(ddb_service=ddb_service, user_table_name=user_table, username=requestor_name)
        if 'train' not in requestor_permissions or \
                ('all' not in requestor_permissions['train'] and 'list' not in requestor_permissions['train']):
            return bad_request(message='user has no permission to train')

        for tr in resp:
            train_job = TrainJob(**(ddb_service.deserialize(tr)))
            model_name = 'not_applied'
            if 'training_params' in train_job.params and 'model_name' in train_job.params['training_params']:
                model_name = train_job.params['training_params']['model_name']

            item = TrainingItem(
                id=train_job.id,
                model_name=model_name,
                status=train_job.job_status.value,
                type=train_job.train_type,
                timestamp=train_job.timestamp,
                sagemaker_train_name=train_job.sagemaker_train_name,
            )

            if train_job.allowed_roles_or_users and check_user_permissions(train_job.allowed_roles_or_users,
                                                                           requestor_roles, requestor_name):
                training_collection.items.append(item)
            elif not train_job.allowed_roles_or_users and \
                    'user' in requestor_permissions and \
                    'all' in requestor_permissions['user']:
                # superuser can view the legacy data
                training_collection.items.append(item)

        return ok(data=training_collection.dict(), decimal=True)
    except Exception as e:
        logger.error(e)
        return bad_request(message=str(e))
