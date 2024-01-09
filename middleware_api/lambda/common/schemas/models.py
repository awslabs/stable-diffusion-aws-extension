from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, HttpUrl


class ModelLink(BaseModel):
    rel: str
    href: HttpUrl
    type: str


class CreateModelParams(BaseModel):
    ckpt_path: Optional[str]
    extra: Optional[bool]
    from_hub: Optional[bool]
    is_512: Optional[bool]
    new_model_token: Optional[str]
    new_model_url: Optional[str]
    shared_src: Optional[str]
    train_unfrozen: Optional[bool]


class Resp(BaseModel):
    s3_output_location: Optional[str]
    config_dict: Optional[dict]


class ModelParams(BaseModel):
    create_model_params: Optional[CreateModelParams]
    resp: Optional[Resp]


class ModelItem(BaseModel):
    id: str
    type: str
    name: str
    status: str
    allowed_roles_or_users: Optional[List[str]]
    output_s3_location: Optional[str]
    params: Optional[ModelParams]
    timestamp: Optional[str]
    s3_location: Optional[str]
    created: Optional[str]
    checkpoint_id: Optional[str]
    links: Optional[List[ModelLink]]

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }


class ModelCollection(BaseModel):
    items: List[ModelItem]
    links: Optional[List[ModelLink]]
    previous_evaluated_key: Optional[str]
    last_evaluated_key: Optional[str]

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }
