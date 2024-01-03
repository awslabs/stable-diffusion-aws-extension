from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, HttpUrl


class RoleLink(BaseModel):
    rel: str
    href: HttpUrl
    type: str


class RoleItem(BaseModel):
    name: str
    creator: str
    permissions: List[str]
    links: Optional[List[RoleLink]]

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }


class UserCollection(BaseModel):
    items: List[RoleItem]
    links: Optional[List[RoleLink]]
