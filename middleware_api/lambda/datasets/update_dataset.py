import json
import logging
import os
from dataclasses import dataclass

from common.ddb_service.client import DynamoDbUtilsService
from common.response import ok, internal_server_error, not_found
from common.types import DatasetItem, DatasetInfo, DatasetStatus, DataStatus

dataset_item_table = os.environ.get('DATASET_ITEM_TABLE')
dataset_info_table = os.environ.get('DATASET_INFO_TABLE')

logger = logging.getLogger('boto3')
ddb_service = DynamoDbUtilsService(logger=logger)


@dataclass
class UpdateDatasetStatusEvent:
    status: str


# PUT /dataset
def handler(raw_event, context):
    event = UpdateDatasetStatusEvent(**json.loads(raw_event['body']))
    dataset_id = raw_event['pathParameters']['id']
    try:
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
        logger.error(e)
        return internal_server_error(message=str(e))
