from enum import Enum, unique


@unique
class LoraTrainType(Enum):
    KOHYA = 'kohya'

@unique
class CheckPointType(Enum):
    SD = "Stable-diffusion"
    LORA = "Lora"

@unique
class NetworkModule(Enum):
    LORA = "networks.lora"


@unique
class TrainFMType(Enum):
    SD_1_5 = "sd_1_5"
    SD_XL = "sd_xl"


KOHYA_TOML_FILE_NAME = 'kohya_config_cloud.toml'
KOHYA_XL_TOML_FILE_NAME = 'kohya_config_cloud_xl.toml'
KOHYA_MODEL_ID = 'kohya'
TRAIN_TYPE = "Stable-diffusion"

PERMISSION_INFERENCE_ALL = "inference:all"
# todo will be remove, compatible with old data
PERMISSION_INFERENCE_LIST = "inference:list"
PERMISSION_INFERENCE_CREATE = "inference:create"

PERMISSION_USER_ALL = "user:all"
# todo will be remove, compatible with old data
PERMISSION_USER_LIST = "user:list"
PERMISSION_USER_CREATE = "user:create"

PERMISSION_TRAIN_ALL = "train:all"
# todo will be remove, compatible with old data
PERMISSION_TRAIN_LIST = "train:list"
PERMISSION_TRAIN_CREATE = "train:create"

PERMISSION_ROLE_ALL = "role:all"
# todo will be remove, compatible with old data
PERMISSION_ROLE_LIST = "role:list"
PERMISSION_ROLE_CREATE = "role:create"

PERMISSION_ENDPOINT_ALL = "sagemaker_endpoint:all"
# todo will be remove, compatible with old data
PERMISSION_ENDPOINT_LIST = "sagemaker_endpoint:list"
PERMISSION_ENDPOINT_CREATE = "sagemaker_endpoint:create"

PERMISSION_CHECKPOINT_ALL = "checkpoint:all"
# todo will be remove, compatible with old data
PERMISSION_CHECKPOINT_LIST = "checkpoint:list"
PERMISSION_CHECKPOINT_CREATE = "checkpoint:create"
