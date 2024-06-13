import json
import logging
import re

import requests

import utils
from aws_extension.cloud_api_manager.api_logger import ApiLogger
from aws_extension.cloud_infer_service.utils import InferManager
from utils import get_variable_from_json

logger = logging.getLogger(__name__)
logger.setLevel(utils.LOGGING_LEVEL)


class SimpleSagemakerInfer(InferManager):

    def parse_lora(self, json_string: str, models):

        prompt = json.loads(json_string)['prompt']
        matches = re.findall(r"<lora:([^:>]+)", prompt)
        lora_list = []
        for match in matches:
            lora_list.append(f"{match}.safetensors")

        models['Lora'] = lora_list

        return models

    def run(self, userid, models, sd_param, is_txt2img, endpoint_type):
        # finished construct api payload
        sd_api_param_json = _parse_api_param_to_json(api_param=sd_param)
        models = self.parse_lora(sd_api_param_json, models)

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
            'inference_type': endpoint_type,
            'task_type': "txt2img" if is_txt2img else "img2img",
            'models': models,
        }
        logger.debug(payload)
        inference_id = None
        headers = {'x-api-key': api_key, 'username': userid}
        response = requests.post(f'{url}inferences', json=payload, headers=headers)
        infer_id = ""
        if 'data' in response.json():
            infer_id = response.json()['data']['inference']['id']
        api_logger = ApiLogger(
            action='inference',
            infer_id=infer_id
        )
        api_logger.req_log(sub_action="CreateInference",
                           method='POST',
                           path=f'{url}inferences',
                           headers=headers,
                           response=response,
                           data=payload,
                           desc="Create inference job on cloud")

        if response.status_code != 201:
            raise Exception(response.json()['message'])

        upload_param_response = response.json()['data']
        if 'inference' in upload_param_response and \
                'api_params_s3_upload_url' in upload_param_response['inference']:
            api_params_s3_upload_url = upload_param_response['inference']['api_params_s3_upload_url']
            upload_s3_resp = requests.put(api_params_s3_upload_url, data=sd_api_param_json)
            upload_s3_resp.raise_for_status()
            api_logger.req_log(sub_action="UploadParameterToS3",
                               method='PUT',
                               path=api_params_s3_upload_url,
                               data=sd_api_param_json,
                               desc="Upload inference parameter to S3 by presigned URL, "
                                    "URL from previous step: CreateInference -> data -> inference -> api_params_s3_upload_url"
                                    "<br/>Just use code to request, not use API tools to upload because they will change the headers to make the request invalid"
                               )
            inference_id = upload_param_response['inference']['id']
            # start run infer
            start_url = f'{url}inferences/{inference_id}/start'
            response = requests.put(start_url, headers={'x-api-key': api_key, 'username': userid})
            api_logger.req_log(sub_action="StartInference",
                               method='PUT',
                               path=start_url,
                               headers=headers,
                               response=response,
                               desc=f"Start inference job on cloud by ID ({inference_id}), ID from previous step: "
                                    "CreateInference -> data -> inference -> id")
            if response.status_code not in [200, 202]:
                logger.error(response.json())
                raise Exception(response.json()['message'])

            # if real-time, return inference data
            if response.status_code == 200:
                return response.json()['data']

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
