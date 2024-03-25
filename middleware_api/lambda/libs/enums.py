from enum import Enum, unique


@unique
class EndpointType(Enum):
    RealTime = "Real-time"
    Serverless = "Serverless"
    Async = "Async"
    List = [RealTime, Async]


@unique
class EndpointStatus(Enum):
    CREATING = "Creating"
    IN_SERVICE = "InService"
    DELETED = "Deleted"
    DELETING = "Deleting"
    FAILED = "Failed"
    UPDATING = "Updating"
    ROLLING_BACK = "RollingBack"


class CreateModelStatus(Enum):
    Initial = 'Initial'
    Creating = 'Creating'
    Complete = 'Complete'
    Fail = 'Fail'


class CheckPointStatus(Enum):
    Initial = 'Initial'
    Active = 'Active'
    Disabled = 'Disabled'


class TrainJobStatus(Enum):
    Initial = 'Initial'
    Training = 'Training'
    Complete = 'Complete'
    Fail = 'Fail'
    Failed = 'Failed'
    Stopped = 'Stopped'
    Starting = 'Starting'
    Downloading = 'Downloading'
    Uploading = 'Uploading'
    Completed = 'Completed'
    Pending = 'Pending'


class DataStatus(Enum):
    Initialed = 'Initialed'
    Enabled = 'Enabled'
    Disabled = 'Disabled'


class DatasetStatus(Enum):
    Initialed = 'Initialed'
    Enabled = 'Enabled'
    Disabled = 'Disabled'


class ComfyEnvPrepareType(Enum):
    ALL = 'default'
    INPUTS = 'inputs'
    NODES = 'nodes'
    MODELS = 'models'
    CUSTOM = 'custom'


class ComfyExecuteType(Enum):
    CREATED = 'created'
    SUCCESS = 'success'
    FAILED = 'failed'


class ComfySyncStatus(Enum):
    INIT = 'init'
    SUCCESS = 'success'
    FAILED = 'failed'


class ComfyTaskType(Enum):
    PREPARE = 'prepare'
    INFERENCE = 'inference'
