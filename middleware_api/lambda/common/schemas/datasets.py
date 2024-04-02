from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, HttpUrl


class DatasetLink(BaseModel):
    rel: str
    href: HttpUrl
    type: str


class DatasetInfoItem(BaseModel):
    name: str
    type: str
    status: str
    preview_url: str
    original_file_name: str


class DatasetItem(BaseModel):
    name: str
    status: str
    s3_location: str
    timestamp: Optional[str]
    description: Optional[str]
    items: Optional[List[DatasetInfoItem]]
    links: Optional[List[DatasetLink]]

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }


class DatasetCollection(BaseModel):
    items: Optional[List[DatasetItem]]
    links: Optional[List[DatasetLink]]
    last_evaluated_key: Optional[str]

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }
