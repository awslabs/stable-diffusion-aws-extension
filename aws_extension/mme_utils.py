import os
import io
import base64
from PIL import Image
from utils import ModelsRef
import mimetypes
import subprocess

try:
    import modules.shared as shared
    from modules import sd_hijack, sd_models, sd_vae
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
def checkspace_and_update_models(selected_models):
    models_num = len(models_type_list)
    space_free_size = selected_models['space_free_size']
    # os.system("df -h")
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
    sd_models.reload_model_weights()
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
    # os.system(f'./tools/s5cmd cp {model_s3_pos} ./')
    # tar_name = model_s3_pos.split('/')[-1]
    # os.system(f"tar xvf {tar_name}")
    # os.system(f"rm {tar_name}")
    # os.system("df -h")

    print(f'./tools/s5cmd cp {model_s3_pos} ./')

    os.system(f'./tools/s5cmd cp {model_s3_pos} ./')
    tar_name = model_s3_pos.split('/')[-1]
    file_type, encoding = mimetypes.guess_type(f'./{tar_name}')
    if file_type == 'tar':
        os.system(f"tar xvf {tar_name}")
        os.system(f"rm {tar_name}")
        os.system("df -h")
    else:
        prefix_name = model_s3_pos.split('.')[0]
        command = ["./tools/s5cmd", "ls", f"{prefix_name}"]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        # 获取文件列表
        file_list = result.stdout.strip().split("\n")
        for s3_file in file_list:
            s3_file_name = s3_file.split("/")[-1]
            download_command = ["./tools/s5cmd", "cp", s3_file, f'./models/{model_type}/{s3_file_name}']
            subprocess.run(download_command, check=True)
            print(f"download {s3_file} to {s3_file_name}")
        print("download finished")
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