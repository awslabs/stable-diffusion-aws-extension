from decimal import Decimal
from typing import Dict
from typing import List, Optional

from pydantic import BaseModel, HttpUrl


class InferenceLink(BaseModel):
    rel: str
    href: HttpUrl
    type: str


class InferenceModel(BaseModel):
    id: str
    model_name: str
    s3: str
    type: str


class InferenceParams(BaseModel):
    input_body_presign_url: Optional[str]
    input_body_s3: Optional[str]
    output_path: Optional[str]
    sagemaker_inference_endpoint_id: Optional[str]
    sagemaker_inference_endpoint_name: Optional[str]
    used_models: Dict[str, List[InferenceModel]]


class InferenceItem(BaseModel):
    id: str
    task_type: str
    status: str
    owner_group_or_role: List[str]
    img_presigned_urls: Optional[List[str]]
    output_presigned_urls: Optional[List[str]]
    params: Optional[InferenceParams]
    sagemaker_raw: Optional[str]
    start_time: Optional[str]
    complete_time: Optional[str]
    endpoint_name: Optional[str]
    links: Optional[List[InferenceLink]]

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }


class InferenceCollection(BaseModel):
    items: Optional[List[InferenceItem]]
    links: Optional[List[InferenceLink]]
    last_evaluated_key: Optional[str]

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }
