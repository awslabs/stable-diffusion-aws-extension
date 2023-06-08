import os
import io
import base64
from PIL import Image
import uuid

import boto3

import modules.shared as shared
from utils import ModelsRef
from modules import sd_hijack, sd_models, sd_vae

CN_MODEL_EXTS = [".pt", ".pth", ".ckpt", ".safetensors"]
models_type_list = ['Stable-diffusion', 'hypernetworks', 'Lora', 'ControlNet', 'embeddings']
models_used_count = {key: ModelsRef() for key in models_type_list}
models_path = {key: None for key in models_type_list}
models_path['Stable-diffusion'] = 'models/Stable-diffusion'
models_path['ControlNet'] = 'models/ControlNet'
models_path['hypernetworks'] = 'models/hypernetworks'
models_path['Lora'] = 'models/Lora'
models_path['embeddings'] = 'embeddings'
disk_path = '/tmp'
#disk_path = '/'
def checkspace_and_update_models(selected_models, checkpoint_info):
    models_num = len(models_type_list)
    space_free_size = selected_models['space_free_size']
    os.system("df -h")
    for type_id in range(models_num):
        model_type = models_type_list[type_id]
        selected_models_name = selected_models[model_type]
        local_models = []
        for path, subdirs, files in os.walk(models_path[model_type]):
            for name in files:
                full_path_name = os.path.join(path, name) 
                name_local = os.path.relpath(full_path_name, models_path[model_type])
                local_models.append(name_local)
        for selected_model_name in selected_models_name:
            models_used_count[model_type].add_models_ref(selected_model_name)
            if selected_model_name in local_models:
                continue
            else:
                st = os.statvfs(disk_path)
                free = (st.f_bavail * st.f_frsize)
                print('!!!!!!!!!!!!current free space is', free)
                if free < space_free_size:
                    #### delete least used model to get more space ########
                    space_check_succese = False
                    for i in range(models_num):
                        type_id_check = (type_id + i)%models_num
                        type_check = models_type_list[type_id_check]
                        selected_models_name_check = selected_models[type_check]
                        print(os.listdir(models_path[type_check]))
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
                                    space_check_succese = True
                                    break
                        if space_check_succese:
                            break
                    if not space_check_succese:
                        print('can not get enough space to download models!!!!!!')
                        return
                ####down load models######
                selected_model_s3_pos = checkpoint_info[model_type][selected_model_name] 
                download_and_update(model_type, selected_model_name, selected_model_s3_pos)
    
    shared.opts.sd_model_checkpoint = selected_models['Stable-diffusion'][0]
    sd_models.reload_model_weights()
    sd_vae.reload_vae_weights()

def download_model(model_name, model_s3_pos):
    #download from s3
    os.system(f'./tools/s5cmd cp {model_s3_pos} ./')
    os.system(f"tar xvf {model_name}")

def upload_model(model_type, model_name, model_s3_pos):
    #upload model to s3
    os.system(f"tar cvf {model_name} {models_path[model_type]}/{model_name}")
    os.system(f'./tools/s5cmd cp {model_name} {model_s3_pos}') 

def download_and_update(model_type, model_name, model_s3_pos):
    #download from s3
    os.system(f'./tools/s5cmd cp {model_s3_pos} ./')
    tar_name = model_s3_pos.split('/')[-1]
    os.system(f"tar xvf {tar_name}")
    os.system(f"rm {tar_name}")
    os.system("df -h")
    if model_type == 'Stable-diffusion':
        sd_models.list_models()
    if model_type == 'hypernetworks':
        shared.reload_hypernetworks()
    if model_type == 'embeddings':
        sd_hijack.model_hijack.embedding_db.load_textual_inversion_embeddings(force_reload=True)
    if model_type == 'ControlNet':
        #sys.path.append("extensions/sd-webui-controlnet/scripts/")
        from scripts import global_state
        global_state.update_cn_models()
        #sys.path.remove("extensions/sd-webui-controlnet/scripts/")

def decode_base64_to_image(encoding):
    if encoding.startswith("data:image/"):
        encoding = encoding.split(";")[1].split(",")[1]
    return Image.open(io.BytesIO(base64.b64decode(encoding)))

def file_to_base64(file_path) -> str:
    with open(file_path, "rb") as f:
        im_b64 = base64.b64encode(f.read())
        return str(im_b64, 'utf-8')

def get_bucket_and_key(s3uri):
        pos = s3uri.find('/', 5)
        bucket = s3uri[5 : pos]
        key = s3uri[pos + 1 : ]
        return bucket, key

def post_invocations(selected_models, b64images):
    #generated_images_s3uri = os.environ.get('generated_images_s3uri', None)
    bucket = selected_models['bucket']
    s3_base_dir = selected_models['base_dir']
    output_folder = selected_models['output']
    generated_images_s3uri = os.path.join(bucket,s3_base_dir,output_folder)
    s3_client = boto3.client('s3')
    if generated_images_s3uri:
        #generated_images_s3uri = f'{generated_images_s3uri}{username}/'
        bucket, key = get_bucket_and_key(generated_images_s3uri)
        for b64image in b64images:
            image = decode_base64_to_image(b64image)
            output = io.BytesIO()
            image.save(output, format='JPEG')
            image_id = str(uuid.uuid4())
            s3_client.put_object(
                Body=output.getvalue(),
                Bucket=bucket,
                Key=f'{key}/{image_id}.png')