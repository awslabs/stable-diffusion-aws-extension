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

# used_models = {
#                 'space_free_size': 400000000.0,  # sys.float_info.max
#                 'Stable-diffusion': [{'s3': 's3://xl11-sds3aigcbucket7db76a0b-clyjqez4tx3m/Stable-diffusion/checkpoint/custom/588cb29d-95d7-40ed-86c3-b69f94f8d1a1', 'id': '3d3dbd57-e2f1-402e-a239-b4d1542466fe', 'model_name': 'sd_xl_base_1.0.safetensors', 'type': 'Stable-diffusion'},
#                                      {'s3': 's3://xl11-sds3aigcbucket7db76a0b-clyjqez4tx3m/Stable-diffusion/checkpoint/custom/47563bb8-92e4-4f05-bee5-a43193d8d0f5', 'id': '3d3dbd57-e2f1-402e-a239-b4d1542466fe', 'model_name': 'sd_xl_refiner_1.0.safetensors', 'type': 'Stable-diffusion'}
#                                      {'s3': 's3://sd-ui-data-bucket-20230928/Stable-diffusion/checkpoint/custom/697cc942-c6ce-452e-bea5-c2c850ce4879', 'id':, '3d3dbd57-e2f1-402e-a239-b4d1542466fe', 'model_name': 'epicrealism_naturalSinRC1VAE.safetensors', 'type': 'Stable-diffusion'}]
#             }
used_models = {
                'space_free_size': 400000000.0,  # sys.float_info.max
              }

Stable_diffusion_list = [{'s3': 's3://sd-ui-data-bucket-20230928/Stable-diffusion/checkpoint/custom/753c7a30-17aa-4d5c-bb16-faaac0643122', 'id': '3d3dbd57-e2f1-402e-a239-b4d1542466fe', 'model_name': 'majicmixRealistic_v7.safetensors', 'type': 'Stable-diffusion'},
                         {'s3': 's3://sd-ui-data-bucket-20230928/Stable-diffusion/checkpoint/custom/3cfc3a91-e21e-4837-addc-ee74b969280c', 'id': '3d3dbd57-e2f1-402e-a239-b4d1542466fe', 'model_name': 'epicphotogasm_x.safetensors', 'type': 'Stable-diffusion'},
                         {'s3': 's3://sd-ui-data-bucket-20230928/Stable-diffusion/checkpoint/custom/465f562e-de48-4485-950b-18da59f99a00', 'id': '3d3dbd57-e2f1-402e-a239-b4d1542466fe', 'model_name': 'yayoiMix_v25.safetensors', 'type': 'Stable-diffusion'},
                         {'s3': 's3://xl11-sds3aigcbucket7db76a0b-clyjqez4tx3m/Stable-diffusion/checkpoint/custom/588cb29d-95d7-40ed-86c3-b69f94f8d1a1', 'id': '3d3dbd57-e2f1-402e-a239-b4d1542466fe', 'model_name': 'sd_xl_base_1.0.safetensors', 'type': 'Stable-diffusion'}]

VAE_list = [{'s3': 's3://sd-ui-data-bucket-20230928/VAE/checkpoint/custom/0aa260b8-e849-42d1-a2cf-70db6e3d5eb8', 'id': '3d3dbd57-e2f1-402e-a239-b4d1542466fe', 'model_name': 'vae-ft-mse-840000-ema-pruned.safetensors', 'type': 'VAE'}]           

used_models_0 = used_models.copy()
used_models_0['Stable-diffusion'] = [Stable_diffusion_list[1]]
used_models_0['VAE'] = VAE_list
used_models_1 = used_models.copy()
used_models_1['Stable-diffusion'] = [Stable_diffusion_list[1]]
used_models_1['VAE'] = VAE_list
used_models_2 = used_models.copy()
used_models_2['Stable-diffusion'] = [Stable_diffusion_list[2]]

used_models_list = [used_models_0,used_models_1,used_models_2]
json_list = ['s3://diffusers-payloads/payload_case1.json', 's3://diffusers-payloads/payload_case2.json', 's3://diffusers-payloads/payload_case3.json']

payload = {
            "task": "txt2img",
            "username": "test",
            "models": used_models_0,
            "param_s3": 's3://diffusers-payloads/txt2img_controlnet_openpose_new.json'
        }
#'s3://xl11-sds3aigcbucket7db76a0b-clyjqez4tx3m/txt2img/infer_v2/5923a628-b593-4f2a-80d5-682b620afe2c/api_param.json'
# txt2img_esrgan.json txt2img_hr_civita.json txt2img_hr_NMKD.json
start_time = time.time()
used_models_3 = used_models.copy()
used_models_3['Stable-diffusion'] = [Stable_diffusion_list[1]]

payload = {
            "task": "txt2img",
            "username": "test",
            "models": used_models_3,
            "param_s3": 's3://diffusers-payloads/txt2img_debug.json'
        }
#txt2img_debug

url = "http://127.0.0.1:8080"

response_diffuer = requests.post(url=f'{url}/invocations', json=payload)
r = response_diffuer.json()
id = 0
for image_base64 in r['images']:
    image = Image.open(io.BytesIO(base64.b64decode(image_base64.split(",",1)[0])))
    image.save('output_diffuser_case_%d_%d.png'%(15,id))
    id += 1

exit()
for i in range(len(json_list)):
    print('!!!!!!!!', i)
    payload['models'] = used_models_list[i]
    payload['param_s3'] = json_list[i]
    print(payload['models'])
    response_diffuer = requests.post(url=f'{url}/invocations', json=payload)
    r = response_diffuer.json()
    id = 0
    for image_base64 in r['images']:
        image = Image.open(io.BytesIO(base64.b64decode(image_base64.split(",",1)[0])))
        image.save('output_diffuser_case_%d_%d.png'%(i,id))
        id += 1
print(f"diffuser average run time is {(time.time()-start_time)/len(json_list)}")
#print(response_diffuer.json())



