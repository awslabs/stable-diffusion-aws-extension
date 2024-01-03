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
    input_body_presign_url: str
    input_body_s3: str
    output_path: str
    sagemaker_inference_endpoint_id: str
    sagemaker_inference_endpoint_name: str
    used_models: Dict[str, List[InferenceModel]]


class InferenceItem(BaseModel):
    InferenceJobId: str
    completeTime: str
    image_names: List[str]
    inference_info_name: str
    owner_group_or_role: List[str]
    params: InferenceParams
    sagemakerRaw: str
    startTime: str
    status: str
    taskType: str
    links: Optional[List[InferenceLink]]

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }


class InferenceCollection(BaseModel):
    items: List[InferenceItem]
    links: Optional[List[InferenceLink]]
