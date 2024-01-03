from typing import List, Optional

from pandas._libs.missing import Decimal
from pydantic import BaseModel, HttpUrl


class EndpointLink(BaseModel):
    rel: str
    href: HttpUrl
    type: str


class EndpointItem(BaseModel):
    EndpointDeploymentJobId: str
    autoscaling: bool
    current_instance_count: int
    endpoint_name: str
    endpoint_status: str
    endTime: str
    startTime: str
    max_instance_number: int
    owner_group_or_role: List[str]
    links: Optional[List[EndpointLink]]

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }


class EndpointCollection(BaseModel):
    items: List[EndpointItem]
    links: Optional[List[EndpointLink]]
