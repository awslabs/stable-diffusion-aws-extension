from dataclasses import dataclass
from typing import Optional, Any, List


@dataclass
class InferenceJob:
    InferenceJobId: str
    startTime: str
    status: str
    taskType: str
    owner_group_or_role: Optional[List[str]] = None
    inference_info_name: Optional[Any] = None
    image_names: Optional[Any] = None
    sagemakerRaw: Optional[Any] = None
    completeTime: Optional[Any] = None
    params: Optional[dict[str, Any]] = None


@dataclass
class EndpointDeploymentJob:
    EndpointDeploymentJobId: str
    autoscaling: bool
    max_instance_number: str
    startTime: str
    status: str = None  # deprecated, but can't remove, avoid unexpected keyword argument
    current_instance_count: str = None
    endTime: Optional[str] = None
    endpoint_status: Optional[str] = None
    endpoint_name: Optional[str] = None
    error: Optional[str] = None
    owner_group_or_role: Optional[List[str]] = None


# a copy of aws_extensions.models.InvocationsRequest
@dataclass
class InvocationsRequest:
    task: str
    username: Optional[str]
    param_s3: str
    models: Optional[dict]
