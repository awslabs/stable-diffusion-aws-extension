import json
import requests
import io
import base64
from PIL import Image, PngImagePlugin
import time

start_time = time.time()

url = "http://127.0.0.1:8082"

print("docker api test for clip:")

with open("test.png", "rb") as img:
    test_img = str(base64.b64encode(img.read()), 'utf-8')

payload = {
    "task": "interrogate_clip",
    "interrogate_paylod": {
        "image":test_img,
        "model":"clip"
    }
}

# 
response = requests.post(url=f'{url}/inovations', json=payload)

print(f"run time is {time.time()-start_time}")

# print(f"response is {response}")

r = response.json()

prompt_message = r["caption"]

print(f"prompt message : {prompt_message}")

print("docker api test for deepbooru:")

payload = {
    "task": "interrogate_clip",
    "interrogate_paylod": {
        "image":test_img,
        "model":"deepdanbooru"
    }
}

# 
response = requests.post(url=f'{url}/invocations', json=payload)

print(f"run time is {time.time()-start_time}")

r = response.json()

prompt_message = r["caption"]

print(f"prompt message : {prompt_message}")
