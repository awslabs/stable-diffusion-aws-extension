from dataclasses import dataclass
from typing import Optional, Any


@dataclass
class InferenceJob:
    InferenceJobId: str
    startTime: str
    status: str
    taskType: str
    inference_info_name: Optional[Any] = None
    image_names: Optional[Any] = None
    sagemakerRaw: Optional[Any] = None
    params: Optional[dict[str, Any]] = None


@dataclass
class EndpointDeploymentJob:
    EndpointDeploymentJobId: str
    autoscaling: bool
    endpoint_name: str
    endpoint_status: str
    endTime: str
    error: str
    max_instance_number: str
    startTime: str
    status: str
    owner_group_or_role: str


# a copy of aws_extensions.models.InvocationsRequest
@dataclass
class InvocationsRequest:
    task: str
    username: Optional[str]
    param_s3: str
    models: Optional[dict]
