from enum import Enum, unique


@unique
class EndpointStatus(Enum):
    CREATING = "Creating"
    IN_SERVICE = "InService"
    DELETED = "Deleted"
    FAILED = "Failed"
    UPDATING = "Updating"
    ROLLING_BACK = "RollingBack"
