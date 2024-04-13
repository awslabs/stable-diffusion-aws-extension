from modules.api.models import *
from typing import Optional


class InvocationsRequest(BaseModel):
    task: str
    username: Optional[str]
    # checkpoint_info:Optional[dict]
    models: Optional[dict]
    # txt2img_payload: Optional[StableDiffusionTxt2ImgProcessingAPI]
    # img2img_payload: Optional[StableDiffusionImg2ImgProcessingAPI]
    extras_single_payload: Optional[ExtrasSingleImageRequest]
    extras_batch_payload: Optional[ExtrasBatchImagesRequest]
    interrogate_payload: Optional[InterrogateRequest]
    db_create_model_payload: Optional[str]
    merge_checkpoint_payload: Optional[dict]
    param_s3: Optional[str] = None
    payload_string: Optional[str] = None
    port: Optional[str] = "24001"


class PingResponse(BaseModel):
    status: str
