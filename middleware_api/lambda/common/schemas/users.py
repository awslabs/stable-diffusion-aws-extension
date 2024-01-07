from typing import List, Optional

from pydantic import BaseModel, HttpUrl
from pydantic.types import Decimal


class UserLink(BaseModel):
    rel: str
    href: HttpUrl
    type: str


class UserItem(BaseModel):
    name: str
    creator: str
    roles: List[str]
    permissions: List[str]
    password: Optional[str]
    links: Optional[List[UserLink]]

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }


class UserCollection(BaseModel):
    items: List[UserItem]
    links: Optional[List[UserLink]]
    previous_evaluated_key: Optional[str]
    last_evaluated_key: Optional[str]

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }
