from enum import Enum, unique


@unique
class LoraTrainType(Enum):
    KOHYA = 'kohya'


KOHYA_TOML_FILE_NAME = 'kohya_config_cloud.toml'
KOHYA_MODEL_ID = 'kohya'
TRAIN_TYPE = "Stable-diffusion"

PERMISSION_INFERENCE_ALL = "inference:all"
PERMISSION_USER_ALL = "user:all"
PERMISSION_TRAIN_ALL = "train:all"
PERMISSION_ROLE_ALL = "role:all"
PERMISSION_ENDPOINT_ALL = "sagemaker_endpoint:all"
PERMISSION_CHECKPOINT_ALL = "checkpoint:all"
PERMISSION_DATASET_ALL = "dataset:all"
