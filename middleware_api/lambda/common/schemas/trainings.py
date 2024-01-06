from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, HttpUrl


class TrainingLink(BaseModel):
    rel: str
    href: HttpUrl
    type: str


class TrainingParams(BaseModel):
    resp: map
    training_params: map


class TrainingItem(BaseModel):
    id: str
    type: str
    status: str
    timestamp: str
    checkpoint_id: Optional[str]
    model_id: Optional[str]
    model_name: Optional[str]
    input_s3_location: Optional[str]
    sagemaker_sfn_arn: Optional[str]
    sagemaker_train_name: Optional[str]
    allowed_roles_or_users: Optional[List[str]]
    params: Optional[TrainingParams]
    links: Optional[List[TrainingLink]]

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }


class TrainingCollection(BaseModel):
    items: Optional[List[TrainingItem]]
    links: Optional[List[TrainingLink]]
    previous_evaluated_key: Optional[str]
    last_evaluated_key: Optional[str]

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }
