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
    allowed_roles_or_users: List[str]
    checkpoint_id: str
    input_s3_location: str
    job_status: str
    model_id: str
    sagemaker_sfn_arn: str
    sagemaker_train_name: str
    timestamp: str
    train_type: str
    params: TrainingParams
    links: Optional[List[TrainingLink]]

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }


class TrainingCollection(BaseModel):
    items: List[TrainingItem]
    links: Optional[List[TrainingLink]]
