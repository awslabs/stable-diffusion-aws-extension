import json
import logging
import os
from dataclasses import dataclass

from aws_lambda_powertools import Tracer

from common.const import PERMISSION_TRAIN_ALL
from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok, not_found
from libs.data_types import DatasetItem, DatasetInfo, DatasetStatus, DataStatus
from libs.utils import permissions_check, response_error

tracer = Tracer()
dataset_item_table = os.environ.get('DATASET_ITEM_TABLE')
dataset_info_table = os.environ.get('DATASET_INFO_TABLE')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)


@dataclass
class UpdateDatasetStatusEvent:
    status: str


# PUT /dataset
@tracer.capture_lambda_handler
def handler(raw_event, context):
    try:
        logger.info(json.dumps(raw_event))
        event = UpdateDatasetStatusEvent(**json.loads(raw_event['body']))
        dataset_id = raw_event['pathParameters']['id']

        permissions_check(raw_event, [PERMISSION_TRAIN_ALL])

        raw_dataset_info = ddb_service.get_item(table=dataset_info_table, key_values={
            'dataset_name': dataset_id
        })
        if not raw_dataset_info or len(raw_dataset_info) == 0:
            return not_found(message=f'dataset {dataset_id} is not found')

        dataset_info = DatasetInfo(**raw_dataset_info)
        new_status = DatasetStatus[event.status]
        dataset_info.dataset_status = new_status
        ddb_service.update_item(table=dataset_info_table,
                                key={'dataset_name': dataset_info.dataset_name},
                                field_name='dataset_status', value=new_status.value
                                )
        dataset_items = ddb_service.query_items(table=dataset_item_table, key_values={
            'dataset_name': dataset_info.dataset_name,
        })

        updates_items = []
        for row in dataset_items:
            item = DatasetItem(**ddb_service.deserialize(row))
            item.data_status = DataStatus[event.status]
            updates_items.append(item.__dict__)

        ddb_service.batch_put_items(table_items={
            dataset_item_table: updates_items
        })

        return ok(data={
            'datasetName': dataset_info.dataset_name,
            'status': dataset_info.dataset_status.value,
        })

    except Exception as e:
        return response_error(e)
