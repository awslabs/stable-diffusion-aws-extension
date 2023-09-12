import json
import requests
import io
import base64
from PIL import Image, PngImagePlugin
import time
import os
from gradio.processing_utils import encode_pil_to_base64
import sys

start_time = time.time()
count = 1

url = "http://127.0.0.1:8080"

params_file = 'api_param_reference_only.json' #'payload.json'
f = open(params_file)
aigc_params = json.load(f)

payload_file = 'payload.json'
f = open(payload_file)
aigc_payload = json.load(f)

payload={}
payload['task'] = 'txt2img'
payload['txt2img_payload'] = {"denoising_strength": 0.75, "prompt": "a girl", "styles": [], "seed": 2, "subseed": 2, "subseed_strength": 0.0, "seed_resize_from_h": 0, "seed_resize_from_w": 0, "sampler_name": "Euler a", "batch_size": 2, "n_iter": 1, "steps": 20, "cfg_scale": 7, "width": 512, "height": 512, "negative_prompt": "", "eta": 1, "s_churn": 0, "s_tmax": 1, "s_tmin": 0, "s_noise": 1, "override_settings": {}, "script_name": "", "script_args": []}
# payload['txt2img_payload']['alwayson_scripts'] = aigc_params['alwayson_scripts']
# payload["txt2img_payload"]["prompt"] = aigc_params["prompt"]
# payload["txt2img_payload"]["seed"] = aigc_params["seed"]
# payload["txt2img_payload"]["subseed"] = aigc_params["subseed"]
# payload["txt2img_payload"]["steps"] = 20 #aigc_params["steps"]
# payload["txt2img_payload"]["width"] = aigc_params["width"]
# payload["txt2img_payload"]["height"] = aigc_params["height"]
# payload["txt2img_payload"]["cfg_scale"] = aigc_params["cfg_scale"]
# payload["txt2img_payload"]["negative_prompt"] = aigc_params["negative_prompt"]
# payload['txt2img_payload']['batch_size'] = 1



#payload['task'] = 'img2img'
#payload['img2img_payload'] = aigc_payload['img2img_payload']

for i in range(count):
    response_diffuer = requests.post(url=f'{url}/invocations', json=payload)

print(f"diffuser average run time is {(time.time()-start_time)/count}")


start_time = time.time()
# for i in range(count):
#     response_local = requests.post(url=f'{url}/sdapi/v1/img2img', json=payload['img2img_payload'])

for i in range(count):
   response_local = requests.post(url=f'{url}/sdapi/v1/txt2img', json=payload['txt2img_payload'])

print(f"webui average run time is {(time.time()-start_time)/count}")

r = response_diffuer.json()

id = 0
for i in r['images']:
    image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0])))

    png_payload = {
        "image": "data:image/png;base64," + i
    }
    response2 = requests.post(url=f'{url}/sdapi/v1/png-info', json=png_payload)

    pnginfo = PngImagePlugin.PngInfo()
    pnginfo.add_text("parameters", response2.json().get("info"))
    image.save('output_diffuser_%d.png'%id, pnginfo=pnginfo)
    id += 1

r = response_local.json()

id = 0
for i in r['images']:
    image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0])))

    png_payload = {
        "image": "data:image/png;base64," + i
    }
    response2 = requests.post(url=f'{url}/sdapi/v1/png-info', json=png_payload)

    pnginfo = PngImagePlugin.PngInfo()
    pnginfo.add_text("parameters", response2.json().get("info"))
    image.save('output_local_%d.png'%id, pnginfo=pnginfo)
    id += 1

for i in range(count):
    response_diffuer = requests.post(url=f'{url}/invocations', json=payload)

print(f"diffuser2 average run time is {(time.time()-start_time)/count}")


start_time = time.time()

for i in range(count):
   response_local = requests.post(url=f'{url}/sdapi/v1/txt2img', json=payload['txt2img_payload'])

print(f"webui average run time is {(time.time()-start_time)/count}")

r = response_diffuer.json()

id = 0
for i in r['images']:
    image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0])))

    png_payload = {
        "image": "data:image/png;base64," + i
    }
    response2 = requests.post(url=f'{url}/sdapi/v1/png-info', json=png_payload)

    pnginfo = PngImagePlugin.PngInfo()
    pnginfo.add_text("parameters", response2.json().get("info"))
    image.save('output_diffuser2_%d.png'%id, pnginfo=pnginfo)
    id += 1

r = response_local.json()

id = 0
for i in r['images']:
    image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0])))

    png_payload = {
        "image": "data:image/png;base64," + i
    }
    response2 = requests.post(url=f'{url}/sdapi/v1/png-info', json=png_payload)

    pnginfo = PngImagePlugin.PngInfo()
    pnginfo.add_text("parameters", response2.json().get("info"))
    image.save('output_local2_%d.png'%id, pnginfo=pnginfo)
    id += 1