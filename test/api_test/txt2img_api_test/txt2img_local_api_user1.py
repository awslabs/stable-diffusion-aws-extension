import requests
import time
start_time = time.time()

url = "http://127.0.0.1:8080"

task_type = 'txt2img'
print(f"Task Type: {task_type}")
from _types import InvocationsRequest

def custom_serializer(obj):
    if isinstance(obj, InvocationsRequest):
        return obj.__dict__  # 将对象转换为字典
    raise TypeError("Object not serializable")

request = InvocationsRequest(task='txt2img', username='test',param_s3='mytestbuckets3/api_param.json',models={'space_free_size': 40000000000.0, 'Stable-diffusion': [{'s3': 's3testurlbucket/Stable-diffusion/checkpoint/custom/13fb3cd2-3d7c-41dd-8fcb-78cb8a86297e','id': '13fb3cd2-3d7c-41dd-8fcb-78cb8a86297e','model_name': 'abyssorangemix3AOM3_aom3.safetensors', 'type': 'Stable-diffusion'}]})

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

