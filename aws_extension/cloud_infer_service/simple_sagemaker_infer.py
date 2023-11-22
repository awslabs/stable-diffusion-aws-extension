import logging
import requests
from datetime import datetime

import utils
from aws_extension.cloud_infer_service.utils import InferManager
from utils import get_variable_from_json

logger = logging.getLogger(__name__)
logger.setLevel(utils.LOGGING_LEVEL)


class SimpleSagemakerInfer(InferManager):

    def run(self, userid, models, sd_param, is_txt2img):
        # finished construct api payload
        sd_api_param_json = _parse_api_param_to_json(api_param=sd_param)
        if logging.getLogger().getEffectiveLevel() == logging.DEBUG:
            # debug only, may delete later
            with open(f'api_{"txt2img" if is_txt2img else "img2img"}_param.json', 'w') as f:
                f.write(sd_api_param_json)

        # create an inference and upload to s3
        # Start creating model on cloud.
        url = get_variable_from_json('api_gateway_url')
        api_key = get_variable_from_json('api_token')
        if not url or not api_key:
            logger.debug("Url or API-Key is not setting.")
            return

        payload = {
            # 'sagemaker_endpoint_name': sagemaker_endpoint,
            'user_id': userid,
            'task_type': "txt2img" if is_txt2img else "img2img",
            'models': models,
            'filters': {
                'createAt': datetime.now().timestamp(),
                'creator': 'sd-webui'
            },
        }
        logger.debug(payload)
        inference_id = None

        response = requests.post(f'{url}inference/v2', json=payload, headers={'x-api-key': api_key})
        response.raise_for_status()
        upload_param_response = response.json()
        if upload_param_response['statusCode'] != 200:
            raise Exception(upload_param_response['errMsg'])

        if 'inference' in upload_param_response and \
                'api_params_s3_upload_url' in upload_param_response['inference']:
            upload_s3_resp = requests.put(upload_param_response['inference']['api_params_s3_upload_url'],
                                          data=sd_api_param_json)
            upload_s3_resp.raise_for_status()
            inference_id = upload_param_response['inference']['id']
            # start run infer
            response = requests.put(f'{url}inference/v2/{inference_id}/run', json=payload,
                                    headers={'x-api-key': api_key})
            response.raise_for_status()

        return inference_id


def _parse_api_param_to_json(api_param):
    import json
    from PIL import Image, PngImagePlugin
    from io import BytesIO
    import base64
    import numpy
    import enum

    def get_pil_metadata(pil_image):
        # Copy any text-only metadata
        metadata = PngImagePlugin.PngInfo()
        for key, value in pil_image.info.items():
            if isinstance(key, str) and isinstance(value, str):
                metadata.add_text(key, value)

        return metadata

    def encode_pil_to_base64(pil_image):
        with BytesIO() as output_bytes:
            pil_image.save(output_bytes, "PNG", pnginfo=get_pil_metadata(pil_image))
            bytes_data = output_bytes.getvalue()

        base64_str = str(base64.b64encode(bytes_data), "utf-8")
        return "data:image/png;base64," + base64_str

    def encode_no_json(obj):
        if isinstance(obj, numpy.ndarray):
            return encode_pil_to_base64(Image.fromarray(obj))
            # return obj.tolist()
            # return "base64 str"
        elif isinstance(obj, Image.Image):
            return encode_pil_to_base64(obj)
        elif isinstance(obj, enum.Enum):
            return obj.value
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            logger.debug(f'may not able to json dumps {type(obj)}: {str(obj)}')
            return str(obj)

    return json.dumps(api_param, default=encode_no_json)
