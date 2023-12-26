import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, List

from common.ddb_service.client import DynamoDbUtilsService
from common.response import bad_request, internal_server_error, created
from common.util import get_s3_presign_urls
from libs.data_types import DatasetItem, DatasetInfo, DatasetStatus, DataStatus
from libs.utils import get_permissions_by_username, get_user_roles

dataset_item_table = os.environ.get('DATASET_ITEM_TABLE')
dataset_info_table = os.environ.get('DATASET_INFO_TABLE')
bucket_name = os.environ.get('S3_BUCKET')
user_table = os.environ.get('MULTI_USER_TABLE')

logger = logging.getLogger('boto3')
ddb_service = DynamoDbUtilsService(logger=logger)


@dataclass
class DataUploadEvent:
    filename: str
    name: str
    type: str
    params: dict[str, Any]


@dataclass
class DatasetCreateEvent:
    dataset_name: str
    content: List[DataUploadEvent]
    params: dict[str, Any]
    creator: str

    def get_filenames(self):
        return [f.filename for f in self.content]

    def __post_init__(self):
        parsed_arr = []
        for entry in self.content:
            parsed_arr.append(DataUploadEvent(**entry))

        self.content = parsed_arr


# POST /datasets
def handler(raw_event, context):
    event = DatasetCreateEvent(**json.loads(raw_event['body']))

    try:
        creator_permissions = get_permissions_by_username(ddb_service, user_table, event.creator)
        if 'train' not in creator_permissions \
                or ('all' not in creator_permissions['train'] and 'create' not in creator_permissions['train']):
            return bad_request(message=f'user {event.creator} has not permission to create a train job')

        user_roles = get_user_roles(ddb_service, user_table, event.creator)
        timestamp = datetime.now().timestamp()
        new_dataset_info = DatasetInfo(
            dataset_name=event.dataset_name,
            timestamp=timestamp,
            dataset_status=DatasetStatus.Initialed,
            params=event.params,
            allowed_roles_or_users=user_roles,
        )

        presign_url_map = get_s3_presign_urls(
            bucket_name=bucket_name,
            base_key=new_dataset_info.get_s3_key(),
            filenames=event.get_filenames()
        )
        dataset = []
        for f in event.content:
            params = f.params
            if not params or len(params) == 0:
                params = {}

            params['original_file_name'] = f.filename
            dataset.append(DatasetItem(
                dataset_name=new_dataset_info.dataset_name,
                sort_key=f'{timestamp}_{f.name}',
                name=f.name,
                type=f.type,
                data_status=DataStatus.Initialed,
                params=params,
                allowed_roles_or_users=user_roles
            ).__dict__)

        ddb_service.batch_put_items({
            dataset_item_table: dataset,
            dataset_info_table: [new_dataset_info.__dict__]
        })

        data = {
            'datasetName': new_dataset_info.dataset_name,
            's3PresignUrl': presign_url_map
        }

        return created(data=data)
    except Exception as e:
        logger.error(e)
        return internal_server_error(message=str(e))
