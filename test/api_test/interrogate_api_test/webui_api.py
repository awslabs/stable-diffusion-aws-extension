import json
import requests
import io
import base64
from PIL import Image, PngImagePlugin
import time

start_time = time.time()

url = "http://127.0.0.1:7860"

print("webui api test for clip:")

with open("test.png", "rb") as img:
    test_img = str(base64.b64encode(img.read()), 'utf-8')

payload = {
    "image":test_img,
    "model":"clip"
}

# 
response = requests.post(url=f'{url}/sdapi/v1/interrogate', json=payload)

print(f"run time is {time.time()-start_time}")

# print(f"response is {response}")

r = response.json()

prompt_message = r["caption"]

print(f"prompt message : {prompt_message}")

print("webui api test for deepbooru:")

payload = {
    "image":test_img,
    "model":"deepdanbooru"
}

# 
response = requests.post(url=f'{url}/sdapi/v1/interrogate', json=payload)

print(f"run time is {time.time()-start_time}")

r = response.json()

prompt_message = r["caption"]

print(f"prompt message : {prompt_message}")
