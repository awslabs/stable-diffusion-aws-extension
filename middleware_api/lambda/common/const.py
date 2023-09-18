from enum import Enum, unique


@unique
class LoraTrainType(Enum):
    KOHYA = "kohya"
    DREAM_BOOTH = "dreambooth"


KOHYA_TOML_FILE_NAME = 'kohya_config_cloud.toml'
