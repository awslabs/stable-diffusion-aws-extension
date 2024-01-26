from typing import List, Optional

from decimal import Decimal
from pydantic import BaseModel, HttpUrl


class EndpointLink(BaseModel):
    rel: str
    href: HttpUrl
    type: str


class EndpointItem(BaseModel):
    id: str
    autoscaling: bool
    name: str
    status: str
    max_instance_number: int
    owner_group_or_role: List[str]
    start_time: str
    # compatible with older data
    current_instance_count: Optional[str]
    end_time: Optional[str]
    links: Optional[List[EndpointLink]]

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }


class EndpointCollection(BaseModel):
    items: Optional[List[EndpointItem]]
    links: Optional[List[EndpointLink]]
    previous_evaluated_key: Optional[str]
    last_evaluated_key: Optional[str]

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }
