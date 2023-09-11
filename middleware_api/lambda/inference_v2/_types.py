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
    endpoint_name: str
    endpoint_status: str
    endTime: str
    max_instance_number: str
    startTime: str
    status: str
    error: Optional[str] = None
    owner_group_or_role: Optional[List[str]] = None



# a copy of aws_extensions.models.InvocationsRequest
@dataclass
class InvocationsRequest:
    task: str
    username: Optional[str]
    param_s3: str
    models: Optional[dict]
