from dataclasses import dataclass
from typing import Optional, Any

import boto3.dynamodb.types


Default_Role = 'IT Operator'

@dataclass
class _PartitionKeys:
    user = 'user'
    role = 'role'
    # permission = 'permission'


PARTITION_KEYS = _PartitionKeys()


@dataclass
class BaseMultiUserEntity:
    kind: str
    sort_key: str
    creator: str


@dataclass
class User(BaseMultiUserEntity):
    password: bytes
    roles: [str]
    params: Optional[dict[str, Any]] = None

    def __post_init__(self):
        if type(self.password) in (boto3.dynamodb.types.Binary, boto3.dynamodb.types.BINARY):
            self.password = self.password.value


@dataclass
class Role(BaseMultiUserEntity):
    permissions: [str]
    params: Optional[dict[str, Any]] = None


# @dataclass
# class Permission(BaseMultiUserEntity):
#     name: str
#     params: Optional[dict[str, Any]] = None
