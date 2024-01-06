from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, HttpUrl


class ModelLink(BaseModel):
    rel: str
    href: HttpUrl
    type: str


class CreateModelParams(BaseModel):
    ckpt_path: str
    extra: bool
    from_hub: bool
    is_512: bool
    new_model_name: str
    new_model_token: str
    new_model_url: str
    shared_src: str
    train_unfrozen: str


class Resp(BaseModel):
    config_dict: map
    response: map
    s3_output_location: str


class ModelParams(BaseModel):
    create_model_params: CreateModelParams
    resp: Resp


class ModelItem(BaseModel):
    id: str
    type: str
    name: str
    status: str
    allowed_roles_or_users: List[str]
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
