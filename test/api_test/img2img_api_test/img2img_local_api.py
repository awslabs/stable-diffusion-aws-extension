import json
import requests
import io
import base64
from PIL import Image, PngImagePlugin
import time
import os
import sys
sys.path.append("extensions/stable-diffusion-aws-extension/middleware_api/lambda/inference")
from parse.parameter_parser import json_convert_to_payload
from dotenv import load_dotenv

load_dotenv()

start_time = time.time()

# preapre payload
task_type = 'img2img'
payload_checkpoint_info = json.loads(os.environ['checkpoint_info'])

f = open("extensions/stable-diffusion-aws-extension/test/api_test/json_files/aigc.json")

params_dict = json.load(f)

payload = json_convert_to_payload(params_dict, payload_checkpoint_info, task_type)

print(payload.keys())

# # call local api
# url = "http://127.0.0.1:8082"

# response = requests.post(url=f'{url}/sdapi/v1/img2img', json=payload['img2img_payload'])

# print(f"run time is {time.time()-start_time}")

# print(f"response is {response}")

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
