import json
import requests
import io
import base64
from PIL import Image, PngImagePlugin
import time
import os
from gradio.processing_utils import encode_pil_to_base64
import sys

sys.path.append("../../../middleware_api/lambda/inference")
from parse.parameter_parser import json_convert_to_payload
start_time = time.time()

url = "http://127.0.0.1:8082"

aigc_json_file = "../json_files/txt2img_test.json"
f = open(aigc_json_file)
aigc_params = json.load(f)
checkpoint_info = {'Stable-diffusion': {'v1-5-pruned-emaonly.safetensors': 's3://stable-diffusion-aws-extension-aigcbucketa457cb49-1dga2v0104mc2/Stable-diffusion/checkpoint/icon/062b8574-8380-49d3-a8c4-7d5cf8100bd8/v1-5-pruned-emaonly.safetensors', 'darkSushiMixMix_225D.safetensors': 's3://stable-diffusion-aws-extension-aigcbucketa457cb49-1dga2v0104mc2/Stable-diffusion/checkpoint/custom/b163f4da-2219-4d8e-9cea-6af34662a11b/darkSushiMixMix_225D.safetensors', 'dreamshaper_7.safetensors': 's3://stable-diffusion-aws-extension-aigcbucketa457cb49-1dga2v0104mc2/Stable-diffusion/checkpoint/custom/e0fb5452-ecdf-41bf-8c45-1b63383ae6bc/dreamshaper_7.safetensors', 'v2-1_768-ema-pruned.safetensors': 's3://stable-diffusion-aws-extension-aigcbucketa457cb49-1dga2v0104mc2/Stable-diffusion/checkpoint/custom/3e5f67ca-4f35-40fb-a513-d81f3aea75fe/v2-1_768-ema-pruned.safetensors', 'sd-v1-5-inpainting.ckpt': 's3://stable-diffusion-aws-extension-aigcbucketa457cb49-1dga2v0104mc2/Stable-diffusion/checkpoint/custom/c05338af-98a2-424d-b8cb-33e808a2b007/sd-v1-5-inpainting.ckpt', 'sd_xl_refiner_1.0.safetensors': 's3://stable-diffusion-aws-extension-aigcbucketa457cb49-1dga2v0104mc2/Stable-diffusion/checkpoint/custom/18d6b6fa-e8c1-4d66-b14f-c4786271a7ba/sd_xl_refiner_1.0.safetensors', 'sd_xl_base_0.9.safetensors': 's3://stable-diffusion-aws-extension-aigcbucketa457cb49-1dga2v0104mc2/Stable-diffusion/checkpoint/custom/39b16a9a-2c72-4370-9075-d62606bef914/sd_xl_base_0.9.safetensors', 'sd_xl_base_1.0.safetensors': 's3://stable-diffusion-aws-extension-aigcbucketa457cb49-1dga2v0104mc2/Stable-diffusion/checkpoint/custom/7b24f656-c14c-47a7-9493-5b80652e44ec/sd_xl_base_1.0.safetensors'}, 'embeddings': {'corneo_marin_kitagawa.pt': 's3://stable-diffusion-aws-extension-aigcbucketa457cb49-1dga2v0104mc2/embeddings/checkpoint/custom/f2477fd1-dcb1-4184-ae40-7aca77454b57/corneo_marin_kitagawa.pt'}, 'Lora': {'hanfu_v30Song.safetensors': 's3://stable-diffusion-aws-extension-aigcbucketa457cb49-1dga2v0104mc2/Lora/checkpoint/custom/86bac5b3-e30b-4de7-b33a-608ae3d7ced2/hanfu_v30Song.safetensors'}, 'hypernetworks': {'LuisapKawaii_v1.pt': 's3://stable-diffusion-aws-extension-aigcbucketa457cb49-1dga2v0104mc2/hypernetworks/checkpoint/custom/12716ec7-6846-4c61-96d8-b6cdfb2bfbaf/LuisapKawaii_v1.pt'}, 'ControlNet': {'control_v11p_sd15_inpaint.pth': 's3://stable-diffusion-aws-extension-aigcbucketa457cb49-1dga2v0104mc2/ControlNet/checkpoint/custom/3e48115f-fb0c-4966-828d-384f80ea397c/control_v11p_sd15_inpaint.pth'}, 'sagemaker_endpoint': 'infer-endpoint-1574a8b', 'task_type': 'txt2img'}

task_type = 'txt2img'
print(f"Task Type: {task_type}")
payload = json_convert_to_payload(aigc_params, checkpoint_info, task_type)

model_list = []
model_list.append("v1-5-pruned-emaonly.safetensors")
model_list.append("darkSushiMixMix_225D.safetensors")
model_list.append("sd-v1-5-inpainting.ckpt")
model_list.append("dreamshaper_7.safetensors")
model_list.append("v2-1_768-ema-pruned.safetensors")
model_list.append("v1-5-pruned-emaonly.safetensors")
model_list.append("darkSushiMixMix_225D.safetensors")
model_list.append("sd-v1-5-inpainting.ckpt")
model_list.append("dreamshaper_7.safetensors")
model_list.append("v2-1_768-ema-pruned.safetensors")
model_list.append("v1-5-pruned-emaonly.safetensors")
model_list.append("darkSushiMixMix_225D.safetensors")
model_list.append("sd-v1-5-inpainting.ckpt")
model_list.append("dreamshaper_7.safetensors")
model_list.append("v2-1_768-ema-pruned.safetensors")

import psutil
# import gc

for model in model_list:
    payload["models"]["Stable-diffusion"]= [model]
    response = requests.post(url=f'{url}/invocations', json=payload)

    print(f'Model {model} RAM memory {psutil.virtual_memory()[2]} used: {psutil.virtual_memory()[3]/1000000000 } (GB)')

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
