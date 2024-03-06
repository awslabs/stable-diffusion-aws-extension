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

KOHYA_TOML_FILE_NAME = 'kohya_config_cloud.toml'
KOHYA_MODEL_ID = 'kohya'
