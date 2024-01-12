import os
import io
import base64
from PIL import Image
from modules.api.utils import ModelsRef
import subprocess
import logging
import sys
from modules.shared import opts
from io import BytesIO
from fastapi.exceptions import HTTPException
from PIL import PngImagePlugin,Image
import piexif
import piexif.helper

try:
    import modules.shared as shared
    from modules import sd_models, sd_vae
except Exception:
    print('default modules load fails')

CN_MODEL_EXTS = [".pt", ".pth", ".ckpt", ".safetensors"]
models_type_list = ['Stable-diffusion', 'hypernetworks', 'Lora', 'ControlNet', 'embeddings']
models_used_count = {key: ModelsRef() for key in models_type_list}
models_path = {key: None for key in models_type_list}
models_path['Stable-diffusion'] = 'models/Stable-diffusion'
models_path['ControlNet'] = 'models/ControlNet'
models_path['hypernetworks'] = 'models/hypernetworks'
models_path['Lora'] = 'models/Lora'
models_path['embeddings'] = 'embeddings'
models_path['VAE'] = 'models/VAE'
disk_path = '/tmp'
#disk_path = '/'
TAR_TYPE_FILE = 'application/x-tar'


def checkspace_and_update_models(selected_models):
    models_num = len(models_type_list)
    space_free_size = selected_models['space_free_size']
    os.system("df -h")
    for type_id in range(models_num):
        model_type = models_type_list[type_id]
        if model_type not in selected_models:
            continue

        selected_models_name = selected_models[model_type]
        local_models = []
        for path, subdirs, files in os.walk(models_path[model_type]):
            for name in files:
                full_path_name = os.path.join(path, name)
                name_local = os.path.relpath(full_path_name, models_path[model_type])
                local_models.append(name_local)
        for model in selected_models_name:
            models_used_count[model_type].add_models_ref(model['model_name'])
            if model['model_name'] in local_models:
                continue
            else:
                st = os.statvfs(disk_path)
                free = (st.f_bavail * st.f_frsize)
                print('!!!!!!!!!!!!current free space is', free)
                if free < space_free_size:
                    #### delete least used model to get more space ########
                    space_check_success = False
                    for i in range(models_num):
                        type_id_check = (type_id + i)%models_num
                        type_check = models_type_list[type_id_check]
                        if type_check not in selected_models:
                            continue
                        selected_models_name_check = selected_models[type_check]
                        print(f'check current model folder: {os.listdir(models_path[type_check])}')
                        local_models_check = [f for f in os.listdir(models_path[type_check]) if os.path.splitext(f)[1] in CN_MODEL_EXTS]
                        if len(local_models_check) == 0:
                            continue
                        sorted_local_modles = models_used_count[type_check].get_sorted_models(local_models_check)
                        for local_model in sorted_local_modles:
                            if local_model in selected_models_name_check:
                                continue
                            else:
                                os.remove(os.path.join(models_path[type_check], local_model))
                                print('remove models', os.path.join(models_path[type_check], local_model))
                                models_used_count[type_check].remove_model_ref(local_model)
                                st = os.statvfs(disk_path)
                                free = (st.f_bavail * st.f_frsize)
                                print('!!!!!!!!!!!!current free space is', free)
                                if free > space_free_size:
                                    space_check_success = True
                                    break
                        if space_check_success:
                            break
                    if not space_check_success:
                        print('can not get enough space to download models!!!!!!')
                        return

                ####down load models######
                download_and_update(model_type, f'{model["s3"]}/{model["model_name"]}')

    shared.opts.sd_model_checkpoint = selected_models['Stable-diffusion'][0]["model_name"]
    sd_models.reload_pipeline_weights()
    if 'VAE' in selected_models:
        shared.opts.sd_vae = selected_models['VAE'][0]['model_name']
        sd_vae.reload_vae_weights()

def download_model(model_name, model_s3_pos):
    #download from s3
    os.system(f'./tools/s5cmd cp {model_s3_pos} ./')
    os.system(f"tar xvf {model_name}")

def upload_model(model_type, model_name, model_s3_pos):
    #upload model to s3
    os.system(f"tar cvf {model_name} {models_path[model_type]}/{model_name}")
    os.system(f'./tools/s5cmd cp {model_name} {model_s3_pos}')

def download_and_update(model_type, model_s3_pos):
    #download from s3
    logging.info(f'./tools/s5cmd cp "{model_s3_pos}" ./')
    os.system(f'./tools/s5cmd cp "{model_s3_pos}" ./')
    tar_name = model_s3_pos.split('/')[-1]
    logging.info(tar_name)
    command = f'file --mime-type -b ./"{tar_name}"'
    file_type = subprocess.check_output(command, shell=True).decode('utf-8').strip()
    logging.info(f"file_type is {file_type}")
    if file_type == TAR_TYPE_FILE:
        logging.info("model type is tar")
        os.system(f"tar xvf '{tar_name}'")
        os.system(f"rm '{tar_name}'")
        os.system("df -h")
    else:
        os.system(f"rm '{tar_name}'")  # 使用引号括起文件名
        logging.info(f"model type is origin file type: {file_type}")
        prefix_name = model_s3_pos.split('.')[0]
        os.system(f'./tools/s5cmd cp "{prefix_name}"* ./models/{model_type}/')
        os.system("df -h")
    logging.info("download finished")
    if model_type == 'Stable-diffusion':
        sd_models.list_models()
    if model_type == 'hypernetworks':
        shared.reload_hypernetworks()
    if model_type == 'Lora':
        shared.list_loras()
    if model_type == 'embeddings':
        shared.sd_pipeline.load_textual_inversion(os.path.join(shared.cmd_opts.embeddings_dir, tar_name))
    if model_type == 'ControlNet':
        sys.path.append("extensions/sd-aws-ext/")        
        from scripts import global_state
        global_state.update_cn_models()
        #sys.path.remove("extensions/sd-webui-controlnet/scripts/")

# def decode_base64_to_image(encoding):
#     if encoding.startswith("data:image/"):
#         encoding = encoding.split(";")[1].split(",")[1]
#     return Image.open(io.BytesIO(base64.b64decode(encoding)))

def file_to_base64(file_path) -> str:
    with open(file_path, "rb") as f:
        im_b64 = base64.b64encode(f.read())
        return str(im_b64, 'utf-8')


def decode_base64_to_image(encoding):
    if encoding.startswith("data:image/"):
        encoding = encoding.split(";")[1].split(",")[1]
    try:
        image = Image.open(BytesIO(base64.b64decode(encoding)))
        return image
    except Exception as e:
        raise HTTPException(status_code=500, detail="Invalid encoded image") from e


def encode_pil_to_base64(image):
    with io.BytesIO() as output_bytes:

        if opts.samples_format.lower() == 'png':
            use_metadata = False
            metadata = PngImagePlugin.PngInfo()
            for key, value in image.info.items():
                if isinstance(key, str) and isinstance(value, str):
                    metadata.add_text(key, value)
                    use_metadata = True
            image.save(output_bytes, format="PNG", pnginfo=(metadata if use_metadata else None), quality=opts.jpeg_quality)

        elif opts.samples_format.lower() in ("jpg", "jpeg", "webp"):
            if image.mode == "RGBA":
                image = image.convert("RGB")
            parameters = image.info.get('parameters', None)
            exif_bytes = piexif.dump({
                "Exif": { piexif.ExifIFD.UserComment: piexif.helper.UserComment.dump(parameters or "", encoding="unicode") }
            })
            if opts.samples_format.lower() in ("jpg", "jpeg"):
                image.save(output_bytes, format="JPEG", exif = exif_bytes, quality=opts.jpeg_quality)
            else:
                image.save(output_bytes, format="WEBP", exif = exif_bytes, quality=opts.jpeg_quality)

        else:
            raise HTTPException(status_code=500, detail="Invalid image format")

        bytes_data = output_bytes.getvalue()

    return base64.b64encode(bytes_data)

def get_bucket_and_key(s3uri):
        pos = s3uri.find('/', 5)
        bucket = s3uri[5 : pos]
        key = s3uri[pos + 1 : ]
        return bucket, key

def payload_filter(payload):
    ## filter non-support extensions
    always_keys = payload['alwayson_scripts'].keys()
    unsupport_list = []
    controlnet_support_type_list = ['control_v11p_sd15_canny', 'control_v11p_sd15_tile', 'control_v11p_sd15_depth', 'control_v11p_sd15_inpaint', 'control_v11p_sd15_lineart', 'control_v11p_sd15_mlsd', 'control_v11p_sd15_normalbae', 'control_v11p_sd15_openpose','control_v11p_sd15_scribble', 'control_v11p_sd15_seg','control_v11p_sd15_softedge', 'control_v11p_sd15_lineart_anime']
    for always_key in always_keys:
        if always_key != 'refiner' and always_key != 'controlnet':
            unsupport_list.append(always_key)
        elif always_key == 'controlnet':
            controlnet_args = []
            for unit_control in payload['alwayson_scripts']['controlnet']['args']:
                if unit_control['enabled'] == 'True' and unit_control['model'] in controlnet_support_type_list:
                    controlnet_args.append(unit_control)
    
    payload['controlnet'] = controlnet_args
    for unsupport_key in unsupport_list:
        del payload['alwayson_scripts'][unsupport_key]
    
    if 'enable_hr' in payload.keys():
        if payload['enable_hr']:
            if 'Latent' in payload['hr_upscaler'] or 'Lanczos' in payload['hr_upscaler'] or 'Nearest' in payload['hr_upscaler']:
                payload['hr_upscaler'] = 'R-ESRGAN 4x+'
    
    return payload