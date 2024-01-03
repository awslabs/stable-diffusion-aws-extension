from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, HttpUrl


class DatasetLink(BaseModel):
    rel: str
    href: HttpUrl
    type: str


class DatasetParams(BaseModel):
    description: str


class DatasetItem(BaseModel):
    dataset_name: str
    allowed_roles_or_users: List[str]
    dataset_status: str
    params: DatasetParams
    timestamp: str
    links: Optional[List[DatasetLink]]

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }


class DatasetCollection(BaseModel):
    items: List[DatasetItem]
    links: Optional[List[DatasetLink]]


class DatasetItemParams(BaseModel):
    original_file_name: str


class DatasetInfoItem(BaseModel):
    dataset_name: str
    sort_key: str
    data_status: str
    name: str
    type: str
    params: DatasetItemParams


class DatasetInfoItemCollection(BaseModel):
    items: List[DatasetInfoItem]
