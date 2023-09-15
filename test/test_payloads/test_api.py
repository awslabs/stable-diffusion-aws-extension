import json
import requests
import io
import base64
from PIL import Image, PngImagePlugin
import time
import os
from gradio.processing_utils import encode_pil_to_base64
import sys

# used_models = {
#                 'space_free_size': 400000000.0,  # sys.float_info.max
#                 'embeddings': [{'s3': 's3://xl11-sds3aigcbucket7db76a0b-clyjqez4tx3m/embeddings/checkpoint/custom/d1ce2ce9-ae6c-4e28-859e-6fc3c423422a', 'id': 'd1ce2ce9-ae6c-4e28-859e-6fc3c423422a', 'model_name': 'corneo_marin_kitagawa.pt', 'type': 'embeddings'}, 
#                               {'s3': 's3://xl11-sds3aigcbucket7db76a0b-clyjqez4tx3m/embeddings/checkpoint/custom/46cbb72a-c1d3-4df5-9bd1-e19a115d501d', 'id': '46cbb72a-c1d3-4df5-9bd1-e19a115d501d', 'model_name': 'epiCNegative.pt', 'type': 'embeddings'}, 
#                               {'s3': 's3://xl11-sds3aigcbucket7db76a0b-clyjqez4tx3m/embeddings/checkpoint/custom/e5b1f603-4926-44e7-8a15-a91327960a52', 'id': 'e5b1f603-4926-44e7-8a15-a91327960a52', 'model_name': 'kkw-ph1.bin', 'type': 'embeddings'}, 
#                               {'s3': 's3://xl11-sds3aigcbucket7db76a0b-clyjqez4tx3m/embeddings/checkpoint/custom/2ff38c78-250f-49b0-8680-08705e1c7a31', 'id': '2ff38c78-250f-49b0-8680-08705e1c7a31', 'model_name': 'pureerosface_v1.pt', 'type': 'embeddings'}], 
#                 'Stable-diffusion': [{'s3': 's3://xl11-sds3aigcbucket7db76a0b-clyjqez4tx3m/Stable-diffusion/checkpoint/custom/3d3dbd57-e2f1-402e-a239-b4d1542466fe', 'id': '3d3dbd57-e2f1-402e-a239-b4d1542466fe', 'model_name': 'revAnimated_v122EOL.safetensors', 'type': 'Stable-diffusion'},
#                                     {'s3': 's3://xl11-sds3aigcbucket7db76a0b-clyjqez4tx3m/Stable-diffusion/checkpoint/custom/28efa65c-b862-414c-85b9-747cd09c306e', 'id': '3d3dbd57-e2f1-402e-a239-b4d1542466fe', 'model_name': 'AnythingV5Ink_ink.safetensors', 'type': 'Stable-diffusion'},
#                                     {'s3': 's3://xl11-sds3aigcbucket7db76a0b-clyjqez4tx3m/Stable-diffusion/checkpoint/custom/47563bb8-92e4-4f05-bee5-a43193d8d0f5', 'id': '3d3dbd57-e2f1-402e-a239-b4d1542466fe', 'model_name': 'sd_xl_refiner_1.0.safetensors', 'type': 'Stable-diffusion'},
#                                     {'s3': 's3://xl11-sds3aigcbucket7db76a0b-clyjqez4tx3m/Stable-diffusion/checkpoint/custom/588cb29d-95d7-40ed-86c3-b69f94f8d1a1', 'id': '3d3dbd57-e2f1-402e-a239-b4d1542466fe', 'model_name': 'sd_xl_base_1.0.safetensors', 'type': 'Stable-diffusion'}], 
#                 'Lora': [{'s3': 's3://xl11-sds3aigcbucket7db76a0b-clyjqez4tx3m/Lora/checkpoint/custom/bf222b4a-db0b-4859-9d0c-19d2729ebde4', 'id': 'bf222b4a-db0b-4859-9d0c-19d2729ebde4', 'model_name': 'blindbox_v1_mix.safetensors', 'type': 'Lora'}],
#                 'ControlNet': [{'s3': 's3://xl11-sds3aigcbucket7db76a0b-clyjqez4tx3m/ControlNet/checkpoint/custom/cb29abbb-de58-4176-a0d1-5596de627a71', 'id': '3d3dbd57-e2f1-402e-a239-b4d1542466fe', 'model_name': 'control_v11p_sd15_openpose.pth', 'type': 'ControlNet'},
#                                {'s3': 's3://xl11-sds3aigcbucket7db76a0b-clyjqez4tx3m/ControlNet/checkpoint/custom/08fc3b88-5c1f-4b25-8d5c-7d9f54587d05', 'id': '3d3dbd57-e2f1-402e-a239-b4d1542466fe', 'model_name': 'control_v11p_sd15_seg.pth', 'type': 'ControlNet'}]
#             }
used_models = {
                'space_free_size': 400000000.0,  # sys.float_info.max
                'Stable-diffusion': [{'s3': 's3://xl11-sds3aigcbucket7db76a0b-clyjqez4tx3m/Stable-diffusion/checkpoint/custom/588cb29d-95d7-40ed-86c3-b69f94f8d1a1', 'id': '3d3dbd57-e2f1-402e-a239-b4d1542466fe', 'model_name': 'sd_xl_base_1.0.safetensors', 'type': 'Stable-diffusion'}]
            }
payload = {
            "task": "txt2img",
            "username": "test",
            "models": used_models,
            "param_s3": 's3://diffusers-payloads/txt2img_xl.json'
        }

start_time = time.time()
count = 1

url = "http://127.0.0.1:8080"


for i in range(count):
    response_diffuer = requests.post(url=f'{url}/invocations', json=payload)

print(f"diffuser average run time is {(time.time()-start_time)/count}")
#print(response_diffuer.json())

r = response_diffuer.json()

id = 0
for i in r['images']:
    image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0])))

    # png_payload = {
    #     "image": "data:image/png;base64," + i
    # }

    # response2 = requests.post(url=f'{url}/sdapi/v1/png-info', json=png_payload)

    # pnginfo = PngImagePlugin.PngInfo()
    # pnginfo.add_text("parameters", response2.json().get("info"))
    # image.save('output_diffuser_%d.png'%id, pnginfo=pnginfo)
    image.save('output_diffuser_%d.png'%id)
    id += 1