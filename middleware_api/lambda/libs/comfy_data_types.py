import dataclasses
import datetime
from dataclasses import dataclass
from typing import Optional, List, Any

from libs.enums import ComfyEnvPrepareType, ComfySyncStatus


@dataclass
class ComfyTemplateTable:
    template_name: str
    tag: Optional[str]
    s3_path: str
    create_time: datetime.datetime
    modify_time: datetime.datetime


@dataclass
class ComfyConfigTable:
    config_name: str
    tag: Optional[str]
    config_value: str
    create_time: datetime.datetime
    modify_time: datetime.datetime


@dataclass
class ComfyExecuteTable:
    prompt_id: str
    need_sync: bool


@dataclass
class ComfySyncTable:
    request_id: str
    endpoint_name: str
    instance_count: int
    sync_instance_count: int
    prepare_type: ComfyEnvPrepareType
    need_reboot: bool
    s3_source_path: Optional[str]
    local_target_path: Optional[str]
    endpoint_snapshot: Optional[Any]
    sync_status: ComfySyncStatus
    request_time: datetime.datetime
    response_time: datetime.datetime


@dataclass
class ComfyMessageTable:
    prompt_id: str
    msg_list: Optional[List[str]] = None

