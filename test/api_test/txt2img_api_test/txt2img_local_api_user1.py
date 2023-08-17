import json
import requests
import io
import base64
from PIL import Image, PngImagePlugin
import time
import os
from gradio.processing_utils import encode_pil_to_base64
import sys

# sys.path.append("../../../middleware_api/lambda/inference")
# from parse.parameter_parser import json_convert_to_payload
start_time = time.time()

url = "http://127.0.0.1:8080"

aigc_json_file = "../json_files/txt2img_test1.json"
f = open(aigc_json_file)
aigc_params = json.load(f)
checkpoint_info = {'Stable-diffusion': {'v2-1_768-ema-pruned.safetensors': 's3://stable-diffusion-aws-extension-aigcbucketa457cb49-xfyck6nj4vlo/Stable-diffusion/checkpoint/custom/13896019-1ba4-478a-a5ec-b7e143e840ca/v2-1_768-ema-pruned.safetensors', 'meinamix_meinaV10.safetensors': 's3://stable-diffusion-aws-extension-aigcbucketa457cb49-xfyck6nj4vlo/Stable-diffusion/checkpoint/custom/491803b4-8293-4604-b879-7b1d3fa8f1df/meinamix_meinaV10.safetensors', 'cheeseDaddys_41.safetensors': 's3://stable-diffusion-aws-extension-aigcbucketa457cb49-xfyck6nj4vlo/Stable-diffusion/checkpoint/custom/6fc2a447-a2d6-427c-b520-fef0f4c5ce85/cheeseDaddys_41.safetensors', 'AnythingV5Ink_ink.safetensors': 's3://stable-diffusion-aws-extension-aigcbucketa457cb49-xfyck6nj4vlo/Stable-diffusion/checkpoint/custom/1a0227fc-5bb0-436b-aa87-80d487a536b3/AnythingV5Ink_ink.safetensors', 'camelliamix25DV2_v2.safetensors': 's3://stable-diffusion-aws-extension-aigcbucketa457cb49-xfyck6nj4vlo/Stable-diffusion/checkpoint/custom/2f5063ee-e2ac-40be-b48e-8762dfdc25eb/camelliamix25DV2_v2.safetensors', 'sd-v1-5-inpainting.ckpt': 's3://stable-diffusion-aws-extension-aigcbucketa457cb49-xfyck6nj4vlo/Stable-diffusion/checkpoint/custom/822a6754-87e7-495b-b71a-543cf78cefb2/sd-v1-5-inpainting.ckpt', 'yangk-style_2160_lora.safetensors': 's3://stable-diffusion-aws-extension-aigcbucketa457cb49-xfyck6nj4vlo/Stable-diffusion/checkpoint/custom/7a8ad4b0-0159-4c0d-a5b9-a6692f90902a/yangk-style_2160_lora.safetensors'}, 'embeddings': {}, 'Lora': {}, 'hypernetworks': {}, 'ControlNet': {'control_v11p_sd15_canny.pth': 's3://stable-diffusion-aws-extension-aigcbucketa457cb49-xfyck6nj4vlo/ControlNet/checkpoint/custom/a20edd04-535c-4d85-842b-95c3c743d819/control_v11p_sd15_canny.pth'}, 'sagemaker_endpoint': 'infer-endpoint-5d9775d', 'task_type': 'txt2img'}

task_type = 'txt2img'
print(f"Task Type: {task_type}")
# payload = json_convert_to_payload(aigc_params, checkpoint_info, task_type)

import json
from _types import InvocationsRequest

def custom_serializer(obj):
    if isinstance(obj, InvocationsRequest):
        return obj.__dict__  # 将对象转换为字典
    raise TypeError("Object not serializable")

request = InvocationsRequest(task='txt2img', username='test',param_s3='s3://stabledeffusion110-sds3aigcbucket7db76a0b-f8h2ckvcafgm/txt2img/infer_v2/068e4cb2-3cb3-41d6-8d37-1d9424940aa3/api_param.json',models={'space_free_size': 40000000000.0, 'Stable-diffusion': [{'s3': 's3://stabledeffusion110-sds3aigcbucket7db76a0b-f8h2ckvcafgm/Stable-diffusion/checkpoint/custom/13fb3cd2-3d7c-41dd-8fcb-78cb8a86297e','id': '13fb3cd2-3d7c-41dd-8fcb-78cb8a86297e','model_name': 'abyssorangemix3AOM3_aom3.safetensors', 'type': 'Stable-diffusion'}]})
# request = InvocationsRequest(task='txt2img', username='test', param_s3='s3://stabledeffusion110-sds3aigcbucket7db76a0b-f8h2ckvcafgm/txt2img/infer_v2/068e4cb2-3cb3-41d6-8d37-1d9424940aa3/api_param.json', models={'space_free_size': 40000000000.0, 'M': {'Stable-diffusion': {'L': [{'M': {'s3': {'S': 's3://stabledeffusion110-sds3aigcbucket7db76a0b-f8h2ckvcafgm/Stable-diffusion/checkpoint/custom/13fb3cd2-3d7c-41dd-8fcb-78cb8a86297e'}, 'id': {'S': '13fb3cd2-3d7c-41dd-8fcb-78cb8a86297e'}, 'model_name': {'S': 'abyssorangemix3AOM3_aom3.safetensors'}, 'type': {'S': 'Stable-diffusion'}}}]}}})
# request = InvocationsRequest(task='txt2img', username='test', param_s3={'S': 's3://stabledeffusion110-sds3aigcbucket7db76a0b-f8h2ckvcafgm/txt2img/infer_v2/068e4cb2-3cb3-41d6-8d37-1d9424940aa3/api_param.json'}, models={'space_free_size': 40000000000.0, 'M': {'Stable-diffusion': {'L': [{'M': {'s3': {'S': 's3://stabledeffusion110-sds3aigcbucket7db76a0b-f8h2ckvcafgm/Stable-diffusion/checkpoint/custom/13fb3cd2-3d7c-41dd-8fcb-78cb8a86297e'}, 'id': {'S': '13fb3cd2-3d7c-41dd-8fcb-78cb8a86297e'}, 'model_name': {'S': 'abyssorangemix3AOM3_aom3.safetensors'}, 'type': {'S': 'Stable-diffusion'}}}]}}})
# 使用自定义序列化函数将对象转换为可序列化的字典
# serialized_request = json.dumps(request, default=custom_serializer, indent=4)
model_list = []

model_list.append("yangk-style_2160_lora.safetensors")

import psutil
# import gc
import time

for model in model_list:
    start_time = time.time()

    # payload["models"]["Stable-diffusion"]= [model]
    response = requests.post(url=f'{url}/invocations', json=request.__dict__)

    print(f'Model {model} Running Time {time.time()-start_time} s RAM memory {psutil.virtual_memory()[2]} used: {psutil.virtual_memory()[3]/1000000000 } (GB)')
    print(response.json())
    # gc.collect()

# r = response.json()
# id = 0
# for i in r['images']:
#     image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0])))

#     png_payload = {
#         "image": "data:image/png;base64," + i
#     }
#     response2 = requests.post(url=f'{url}/sdapi/v1/png-info', json=png_payload)

#     pnginfo = PngImagePlugin.PngInfo()
#     pnginfo.add_text("parameters", response2.json().get("info"))
#     image.save('output_%d.png'%id, pnginfo=pnginfo)
#     id += 1
