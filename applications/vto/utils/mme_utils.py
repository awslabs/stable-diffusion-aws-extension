import os
import io
import base64
from PIL import Image
import subprocess
import logging
import sys
from io import BytesIO
from fastapi.exceptions import HTTPException
from PIL import PngImagePlugin,Image


# def decode_base64_to_image(encoding):
#     if encoding.startswith("data:image/"):
#         encoding = encoding.split(";")[1].split(",")[1]
#     return Image.open(io.BytesIO(base64.b64decode(encoding)))

def file_to_base64(file_path) -> str:
    with open(file_path, "rb") as f:
        im_b64 = base64.b64encode(f.read())
        return str(im_b64, 'utf-8')


def decode_base64_to_image(encoding):
    if encoding.startswith("data:image/"):
        encoding = encoding.split(";")[1].split(",")[1]
    try:
        image = Image.open(BytesIO(base64.b64decode(encoding)))
        return image
    except Exception as e:
        raise HTTPException(status_code=500, detail="Invalid encoded image") from e


def encode_pil_to_base64(image):
    with io.BytesIO() as output_bytes:
        use_metadata = False
        metadata = PngImagePlugin.PngInfo()
        for key, value in image.info.items():
            if isinstance(key, str) and isinstance(value, str):
                metadata.add_text(key, value)
                use_metadata = True
        image.save(output_bytes, format="PNG", pnginfo=(metadata if use_metadata else None), quality=80)

        bytes_data = output_bytes.getvalue()

    return base64.b64encode(bytes_data)

def image_to_base64(img):
    """Convert a PIL Image or local image file path to a base64 string for Amazon Bedrock"""
    if isinstance(img, str):
        if os.path.isfile(img):
            print(f"Reading image from file: {img}")
            with open(img, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        else:
            raise FileNotFoundError(f"File {img} does not exist")
    elif isinstance(img, Image.Image):
        print("Converting PIL Image to base64 string")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    else:
        raise ValueError(f"Expected str (filename) or PIL Image. Got {type(img)}")


def get_bucket_and_key(s3uri):
        pos = s3uri.find('/', 5)
        bucket = s3uri[5 : pos]
        key = s3uri[pos + 1 : ]
        return bucket, key

def payload_filter(payload):
    ## filter non-support extensions
    always_keys = payload['alwayson_scripts'].keys()
    unsupport_list = []
    controlnet_support_type_list = ['control_v11p_sd15_canny', 'control_v11p_sd15_tile', 'control_v11p_sd15_depth', 'control_v11p_sd15_inpaint', 'control_v11p_sd15_lineart', 'control_v11p_sd15_mlsd', 'control_v11p_sd15_normalbae', 'control_v11p_sd15_openpose','control_v11p_sd15_scribble', 'control_v11p_sd15_seg','control_v11p_sd15_softedge', 'control_v11p_sd15_lineart_anime']
    for always_key in always_keys:
        if always_key != 'refiner' and always_key != 'controlnet':
            unsupport_list.append(always_key)
        elif always_key == 'controlnet':
            controlnet_args = []
            for unit_control in payload['alwayson_scripts']['controlnet']['args']:
                if unit_control['enabled'] == 'True' and unit_control['model'] in controlnet_support_type_list:
                    controlnet_args.append(unit_control)
    
    payload['controlnet'] = controlnet_args
    for unsupport_key in unsupport_list:
        del payload['alwayson_scripts'][unsupport_key]
    
    if 'enable_hr' in payload.keys():
        if payload['enable_hr']:
            if 'Latent' in payload['hr_upscaler'] or 'Lanczos' in payload['hr_upscaler'] or 'Nearest' in payload['hr_upscaler']:
                payload['hr_upscaler'] = 'R-ESRGAN 4x+'
    
    return payload