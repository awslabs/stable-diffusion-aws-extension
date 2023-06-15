import json
import requests
import base64
import time
import os
import sys
sys.path.append("../../../middleware_api/lambda/inference")
from parse.parameter_parser import json_convert_to_payload

from dotenv import load_dotenv

load_dotenv()

start_time = time.time()

# preapre payload
task_type = ''
payload_checkpoint_info = json.loads(os.environ['checkpoint_info'])

f = open("../json_files/aigc.json")

params_dict = json.load(f)

payload = json_convert_to_payload(params_dict, payload_checkpoint_info, task_type)

print(payload.keys())

# # call local api
# url = "http://localhost:8082"

# print("docker api test for clip:")

# with open("test.png", "rb") as img:
#     test_img = str(base64.b64encode(img.read()), 'utf-8')

# payload = {
#     "task": "interrogate_clip",
#     "interrogate_payload": {
#         "image":test_img,
#         "model":"clip"
#     }
# }

# # 
# response = requests.post(url=f'{url}/invocations', json=payload)

# print(f"run time is {time.time()-start_time}")

# r = response.json()

# prompt_message = r["caption"]

# print(f"prompt message : {prompt_message}")

# print("docker api test for deepbooru:")

# payload = {
#     "task": "interrogate_deepbooru",
#     "interrogate_payload": {
#         "image":test_img,
#         "model":"deepdanbooru"
#     }
# }

# # 
# response = requests.post(url=f'{url}/invocations', json=payload)

# print(f"run time is {time.time()-start_time}")

# r = response.json()

# prompt_message = r["caption"]

# print(f"prompt message : {prompt_message}")
