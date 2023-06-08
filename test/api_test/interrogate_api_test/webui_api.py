import json
import requests
import io
import base64
from PIL import Image, PngImagePlugin
import time

start_time = time.time()

url = "http://127.0.0.1:7860"

print("webui api test for clip")

with open("test.png", "rb") as img:
    test_img = base64.b64encode(img.read())

payload = {
    "image":test_img,
    "model":"clip"
}

# 
response = requests.post(url=f'{url}/invocations', json=payload)

print(f"run time is {time.time()-start_time}")

print(f"response is {response}")

r = response.json()

print(f"json response is {r}")

# for i in r['images']:
#     image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0])))

#     png_payload = {
#         "image": "data:image/png;base64," + i
#     }
#     response2 = requests.post(url=f'{url}/sdapi/v1/png-info', json=png_payload)

#     pnginfo = PngImagePlugin.PngInfo()
#     pnginfo.add_text("parameters", response2.json().get("info"))
#     image.save('output.png', pnginfo=pnginfo)

# print("webui api test for deepdanbooru")

# payload = {
#     "image":"",
#     "model":"deepdanbooru"
# }
