from enum import Enum, unique


@unique
class InferenceStatus(Enum):
    SUCCEED = "succeed"
    FAILED = "failed"
    INPROGRESS = "inprogress"


@unique
class InferenceType(Enum):
    TXT2IMG = "txt2img"
    IMG2IMG = "img2img"
    REMBG = "rembg"
    ESI = "extra-single-image"
