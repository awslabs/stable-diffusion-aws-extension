from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, HttpUrl


class CheckpointLink(BaseModel):
    rel: str
    href: HttpUrl
    type: str


class CheckpointParams(BaseModel):
    created: Optional[str]
    creator: Optional[str]
    message: Optional[str]


class CheckpointItem(BaseModel):
    id: str
    status: str
    type: str
    links: Optional[List[CheckpointLink]]
    allowed_roles_or_users: List[str]
    name: Optional[List[str]]
    params: Optional[CheckpointParams]
    s3_location: Optional[str]
    created: Optional[str]

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }


class CheckpointCollection(BaseModel):
    items: Optional[List[CheckpointItem]]
    links: Optional[List[CheckpointLink]]
    last_evaluated_key: Optional[str]
    page: Optional[int]
    per_page: Optional[int]
    pages: Optional[int]
    total: Optional[int]

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }
