import dataclasses
from dataclasses import dataclass
from typing import Optional, List, Any


@dataclass
class EndpointDeploymentJob:
    EndpointDeploymentJobId: str
    autoscaling: bool
    max_instance_number: str
    startTime: str
    status: str = None  # deprecated, but can't remove, avoid unexpected keyword argument
    instance_type: str = None
    current_instance_count: str = None
    endTime: Optional[str] = None
    endpoint_status: Optional[str] = None
    endpoint_name: Optional[str] = None
    error: Optional[str] = None
    endpoint_type: Optional[str] = "Async"
    owner_group_or_role: Optional[List[str]] = None
    min_instance_number: str = None
    custom_extensions: str = ""

@dataclass
class InferenceJob:
    InferenceJobId: str
    status: str
    taskType: str
    owner_group_or_role: Optional[List[str]] = None
    inference_info_name: Optional[Any] = None
    startTime: Optional[Any] = None
    createTime: Optional[Any] = None
    image_names: Optional[Any] = None
    sagemakerRaw: Optional[Any] = None
    completeTime: Optional[Any] = None
    params: Optional[dict[str, Any]] = None
    inference_type: Optional[str] = None
    payload_string: Optional[str] = None


@dataclass
class DatasetInfo:
    dataset_name: str  # primary key
    timestamp: float
    dataset_status: DatasetStatus
    params: Optional[dict[str, Any]] = None
    allowed_roles_or_users: Optional[list[str]] = None
    prefix: str = ""

    def __post_init__(self):
        if type(self.dataset_status) == str:
            self.dataset_status = DatasetStatus[self.dataset_status]

    def get_s3_key(self):
        if self.prefix:
            return f'dataset/{self.dataset_name}/{self.prefix}'
        return f'dataset/{self.dataset_name}'