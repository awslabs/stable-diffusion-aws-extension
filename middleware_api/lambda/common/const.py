from enum import Enum, unique


@unique
class LoraTrainType(Enum):
    KOHYA = 'kohya'


KOHYA_TOML_FILE_NAME = 'kohya_config_cloud.toml'
KOHYA_MODEL_ID = 'kohya'
TRAIN_TYPE = "Stable-diffusion"
