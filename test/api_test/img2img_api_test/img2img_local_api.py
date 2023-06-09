import json
import requests
import io
import base64
from PIL import Image, PngImagePlugin
import time
import os
from gradio.processing_utils import encode_pil_to_base64
from dotenv import load_dotenv

load_dotenv()

start_time = time.time()

url = "http://127.0.0.1:8080"

#with open("0013.jpg", "rb") as img:
#   init_img = base64.b64encode(img.read())

#print(init_img.decode('utf-8'))

#print('!!!!!!!!!!!')
init_img = encode_pil_to_base64(Image.open("test.png"))

mode = 0
init_images = [init_img]
#sketch = None
#init_img_with_mask = None 
#inpaint_color_sketch = None
#inpaint_color_sketch_orig = None
#init_img_inpaint = None
#init_mask_inpaint = None
#seed_enable_extras = False
#selected_scale_tab = 0 
#"img2img_batch_input_dir": img2img_batch_input_dir,
#"img2img_batch_output_dir": img2img_batch_output_dir,
#"img2img_batch_inpaint_mask_dir": img2img_batch_inpaint_mask_dir,
mask = None
mask_blur = 4
mask_alpha = 0
inpainting_fill = 0
image_cfg_scale = 1.5
resize_mode = 0
inpaint_full_res = False 
inpaint_full_res_padding = 32 
inpainting_mask_invert = 0
initial_noise_multiplier = None
include_init_images = False
img2img_batch_input_dir = ''
img2img_batch_output_dir = ''
img2img_batch_inpaint_mask_dir = ''

task='image-to-image' 
username='test'
checkpoint_info = json.loads(os.environ['checkpoint_info'])
models = json.loads(os.environ["models"])
enable_hr='true'
denoising_strength=0.7
firstphase_width=0
firstphase_height=0
hr_scale=2.0
hr_upscaler="ESRGAN_4x"
hr_second_pass_steps=0
hr_resize_x=0
hr_resize_y=0
prompt='a dancing boy'
styles=[]
seed=-1
subseed=-1
subseed_strength=0.0
seed_resize_from_h=0
seed_resize_from_w=0
sampler_name=None
batch_size=1
n_iter=1
steps=20
cfg_scale=7.0
width=512
height=512
restore_faces=False
tiling=False
do_not_save_samples=False
do_not_save_grid=False
negative_prompt=''
eta=1.0
s_min_uncond=0.0
s_churn=0.0 
s_tmax=1.0 
s_tmin=0.0 
s_noise=1.0 
override_settings={}
sampler_index='Euler a'
script_args=[10, "", ["anyloraCheckpoint_bakedvaeFtmseFp16NOT.safetensors", "abyssorangemix3AOM3_aom3a1b.safetensors", "aniflatmixAnimeFlatColorStyle_v20.safetensors", "babes_20.safetensors", "chilloutmix_NiPrunedFp32Fix.safetensors", "clarity_2.safetensors", "deliberate_v2.safetensors", "dosmix_.safetensors", "dreamshaper_5BakedVae.safetensors", "gameIconInstitute_v21.safetensors", "icerealistic_v21.safetensors", "kotosmix_v10.safetensors", "latexGenerator15By_v09.safetensors", "my_style_132.safetensors", "piying_4000_lora.safetensors", "realisticVisionV20_v20.safetensors", "revAnimated_v122.safetensors", "test1.safetensors", "test2.safetensors", "v2-1_768-ema-pruned.safetensors", "v2-inference-v.safetensors"], 0, "", "", 0, "", "", True, False, False, False, 0]
#script_name='X/Y/Z plot'
payload = {
        "endpoint_name": checkpoint_info['sagemaker_endpoint'],
        "task": "image-to-image", 
        "username": "test",
        "checkpoint_info":checkpoint_info,
        "models":{
            "space_free_size": 2e10,
            "Stable-diffusion": models['Stable-diffusion'],
            "ControlNet": [],
            "hypernetworks": models['hypernetworks'],
            "Lora": models['Lora'],
            "embeddings": models["embeddings"]
        },
        "img2img_payload": {
            "init_images": init_images,
            "mask": mask,
            "mask_blur": mask_blur,
            "initial_noise_multiplier":initial_noise_multiplier,
            "inpainting_fill": inpainting_fill,
            "image_cfg_scale": image_cfg_scale,
            "resize_mode": resize_mode,
            "inpaint_full_res": inpaint_full_res, 
            "inpaint_full_res_padding": inpaint_full_res_padding, 
            "inpainting_mask_invert": inpainting_mask_invert,
            "include_init_images": include_init_images,
            "denoising_strength": denoising_strength, 
            "prompt": prompt, 
            "styles": styles, 
            "seed": seed, 
            "subseed": subseed, 
            "subseed_strength": subseed_strength, 
            "seed_resize_from_h": seed_resize_from_h, 
            "seed_resize_from_w": seed_resize_from_w, 
            "sampler_index": sampler_index, 
            "batch_size": batch_size, 
            "n_iter": n_iter, 
            "steps": steps, 
            "cfg_scale": cfg_scale, 
            "width": width, 
            "height": height, 
            "restore_faces": restore_faces, 
            "tiling": tiling, 
            "negative_prompt": negative_prompt, 
            "eta": eta, 
            "s_churn": s_churn, 
            "s_tmax": s_tmax, 
            "s_tmin": s_tmin, 
            "s_noise": s_noise, 
            "override_settings": override_settings, 
            }, 
        }

response = requests.post(url=f'{url}/sdapi/v1/img2img', json=payload['img2img_payload'])

print(f"run time is {time.time()-start_time}")

print(f"response is {response}")

r = response.json()
id = 0
for i in r['images']:
    image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0])))

    png_payload = {
        "image": "data:image/png;base64," + i
    }
    response2 = requests.post(url=f'{url}/sdapi/v1/png-info', json=png_payload)

    pnginfo = PngImagePlugin.PngInfo()
    pnginfo.add_text("parameters", response2.json().get("info"))
    image.save('output_%d.png'%id, pnginfo=pnginfo)
    id += 1
