from dataclasses import dataclass
from typing import Optional, Any
from enum import Enum


class DataStatus(Enum):
    Initialed = 'Initialed'
    Enabled = 'Enabled'
    Disabled = 'Disabled'


@dataclass
class DatasetItem:
    dataset_name: str     # partition key (s3 key base, not include bucket name)
    sort_key: str         # sorted key: timestamp_name
    name: str             # data name (s3 object key)
    type: str             # data type
    data_status: DataStatus
    params: Optional[dict[str, Any]] = None

    def __post_init__(self):
        if type(self.data_status) == str:
            self.data_status = DataStatus[self.data_status]

    def get_s3_key(self):
        return f'dataset/{self.dataset_name}/{self.name}'


class DatasetStatus(Enum):
    Initialed = 'Initialed'
    Enabled = 'Enabled'
    Disabled = 'Disabled'


@dataclass
class DatasetInfo:
    dataset_name: str                       # primary key
    timestamp: float
    dataset_status: DatasetStatus
    params: Optional[dict[str, Any]] = None

    def __post_init__(self):
        if type(self.dataset_status) == str:
            self.dataset_status = DatasetStatus[self.dataset_status]

    def get_s3_key(self):
        return f'dataset/{self.dataset_name}'
