import json
import requests
import io
import base64
from PIL import Image, PngImagePlugin
import time

start_time = time.time()

url = "http://127.0.0.1:7860"

payload = {
    "image":"",
    "model":"clip"
}

response = requests.post(url=f'{url}/invocations', json=payload)

print(f"run time is {time.time()-start_time}")

print(f"response is {response}")

r = response.json()

for i in r['images']:
    image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0])))

    png_payload = {
        "image": "data:image/png;base64," + i
    }
    response2 = requests.post(url=f'{url}/sdapi/v1/png-info', json=png_payload)

    pnginfo = PngImagePlugin.PngInfo()
    pnginfo.add_text("parameters", response2.json().get("info"))
    image.save('output.png', pnginfo=pnginfo)
