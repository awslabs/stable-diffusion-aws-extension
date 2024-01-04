from enum import Enum, unique


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
    Stopped = 'Stopped'


class DataStatus(Enum):
    Initialed = 'Initialed'
    Enabled = 'Enabled'
    Disabled = 'Disabled'

class DatasetStatus(Enum):
    Initialed = 'Initialed'
    Enabled = 'Enabled'
    Disabled = 'Disabled'
