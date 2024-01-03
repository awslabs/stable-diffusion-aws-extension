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
    allowed_roles_or_users: List[str]
    name: List[str]
    status: str
    params: CheckpointParams
    s3_location: str
    type: str
    links: Optional[List[CheckpointLink]]

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }


class CheckpointCollection(BaseModel):
    items: List[CheckpointItem]
    links: Optional[List[CheckpointLink]]
