import base64
import re
import json
import requests
import threading
import gradio as gr
import os
import sys
import logging
from utils import upload_file_to_s3_by_presign_url
from utils import get_variable_from_json
from utils import tar

logging.basicConfig(filename='sd-aws-ext.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

dreambooth_available = True
def dummy_function(*args, **kwargs):
    return None

try:
    # TODO: Automatically append the dependent module path.
    sys.path.append("extensions/sd_dreambooth_extension")
    # TODO: Do not use the dreambooth status module.
    from dreambooth import shared as dreambooth_shared
    # from extensions.sd_dreambooth_extension.scripts.main import get_sd_models
    from dreambooth.ui_functions import load_model_params
    from dreambooth.dataclasses.db_config import save_config, from_file, Concept
except Exception as e:
    logging.warning("[train]Dreambooth is not installed or can not be imported, using dummy function to proceed.")
    dreambooth_available = False
    dreambooth_shared = dummy_function
    load_model_params = dummy_function
    save_config = dummy_function
    from_file = dummy_function
    Concept = dummy_function

base_model_folder = "models/sagemaker_dreambooth/"


def get_cloud_db_models(types="Stable-diffusion", status="Complete", username=""):
    try:
        api_gateway_url = get_variable_from_json('api_gateway_url')
        if not api_gateway_url:
            print(f"failed to get the api_gateway_url, can not fetch date from remote")
            return []
        url = f"{api_gateway_url}models?"
        if types:
            url = f"{url}types={types}&"
        if status:
            url = f"{url}status={status}&"
        url = url.strip("&")
        encode_type = "utf-8"
        response = requests.get(url=url, headers={
            'x-api-key': get_variable_from_json('api_token'),
            'Authorization': f'Bearer {base64.b16encode(username.encode(encode_type)).decode(encode_type)}'
        }).json()
        model_list = []
        if "items" not in response['data']:
            return []
        for model in response['data']["items"]:
            print(json.dumps(model, indent=4))
            model_list.append(model)
            params = model['params']
            if 'resp' in params:
                db_config = params['resp']['config_dict']
                # TODO:
                model_dir = f"{base_model_folder}/{model['name']}"
                for k in db_config:
                    if type(db_config[k]) is str:
                        db_config[k] = db_config[k].replace("/opt/ml/code/", "")
                        db_config[k] = db_config[k].replace("models/dreambooth/", base_model_folder)

                if not os.path.exists(model_dir):
                    os.makedirs(model_dir, exist_ok=True)
                with open(f"{model_dir}/db_config.json", "w") as db_config_file:
                    json.dump(db_config, db_config_file)
        return model_list
    except Exception as e:
        logger.error(f"Failed to get cloud models {e}")
        return []


def get_cloud_db_model_name_list(username):
    model_list = get_cloud_db_models(username=username)
    if model_list is None:
        model_name_list = []
    else:
        model_name_list = [model['name'] for model in model_list]
    return model_name_list


def hack_db_config(db_config, db_config_file_path, model_name, data_list, class_data_list, local_model_name):
    for k in db_config:
        if k == "model_dir":
            db_config[k] = re.sub(".*/?(models/dreambooth/).+$", f"\\1{model_name}", db_config[k])
        elif k == "pretrained_model_name_or_path":
            db_config[k] = re.sub(".*/?(models/dreambooth/).+(working)$", f"\\1{model_name}/\\2", db_config[k])
        elif k == "model_name":
            db_config[k] = db_config[k].replace(local_model_name, model_name)
        elif k == "concepts_list":
            for concept, data, class_data in zip(db_config[k], data_list, class_data_list):
                concept["instance_data_dir"] = data
                concept["class_data_dir"] = class_data
    with open(db_config_file_path, "w") as db_config_file_w:
        json.dump(db_config, db_config_file_w)


def async_prepare_for_training_on_sagemaker(
        model_id: str,
        model_name: str,
        s3_model_path: str,
        data_path_list: list,
        class_data_path_list: list,
        db_config_path: str,
        model_type: str,
        training_instance_type: str,
        creator: str
):
    url = get_variable_from_json('api_gateway_url')
    api_key = get_variable_from_json('api_token')
    if url is None or api_key is None:
        logger.debug("Url or API-Key is not setting.")
        return
    url += "trainings"
    upload_files = []
    db_config_tar = f"db_config.tar"
    # os.system(f"tar cvf {db_config_tar} {db_config_path}")
    tar(mode='c', archive=db_config_tar, sfiles=[db_config_path], verbose=True)
    upload_files.append(db_config_tar)
    new_data_list = []
    for data_path in data_path_list:
        if len(data_path) == 0:
            new_data_list.append("")
            continue
        if not data_path.startswith("s3://"):
            data_tar = f'data-{data_path.replace("/", "-").strip("-")}.tar'
            new_data_list.append(data_tar)
            print("Pack the data file.")
            # os.system(f"tar cf {data_tar} {data_path}")
            tar(mode='c', archive=data_tar, sfiles=data_path, verbose=False)
            upload_files.append(data_tar)
        else:
            new_data_list.append(data_path)
    new_class_data_list = []
    for class_data_path in class_data_path_list:
        if len(class_data_path) == 0:
            new_class_data_list.append("")
            continue
        if not class_data_path.startswith("s3://"):
            class_data_tar = f'class-data-{class_data_path.replace("/", "-").strip("-")}.tar'
            new_class_data_list.append(class_data_tar)
            upload_files.append(class_data_tar)
            print("Pack the class data file.")
            # os.system(f"tar cf {class_data_tar} {class_data_path}")
            tar(mode='c', archive=class_data_tar, sfiles=[class_data_path], verbose=False)
        else:
            new_class_data_list.append(class_data_path)
    payload = {
        "train_type": model_type,
        "model_id": model_id,
        "filenames": upload_files,
        "params": {
            "training_params": {
                "s3_model_path": s3_model_path,
                "model_name": model_name,
                "model_type": model_type,
                "data_tar_list": new_data_list,
                "class_data_tar_list": new_class_data_list,
                "s3_data_path_list": new_data_list,
                "s3_class_data_path_list": new_class_data_list,
                "training_instance_type": training_instance_type
            }
        },
        'creator': creator,
    }
    print("Post request for upload s3 presign url for train.")
    response = requests.post(url=url, json=payload, headers={
        'x-api-key': api_key
    })
    response.raise_for_status()
    json_response = response.json()
    print(json_response)
    for local_tar_path, s3_presigned_url in json_response['data']["s3PresignUrl"].items():
        upload_file_to_s3_by_presign_url(local_tar_path, s3_presigned_url)
    return json_response


def wrap_load_model_params(model_name):
    origin_model_path = dreambooth_shared.dreambooth_models_path
    setattr(dreambooth_shared, 'dreambooth_models_path', base_model_folder)
    resp = load_model_params(model_name)
    setattr(dreambooth_shared, 'dreambooth_models_path', origin_model_path)
    return resp


def wrap_get_local_config(model_name):
    config = from_file(model_name)
    return config


def wrap_get_cloud_config(model_name):
    origin_model_path = dreambooth_shared.dreambooth_models_path
    setattr(dreambooth_shared, 'dreambooth_models_path', base_model_folder)
    config = from_file(model_name)
    setattr(dreambooth_shared, 'dreambooth_models_path', origin_model_path)
    return config


def wrap_save_config(model_name):
    origin_model_path = dreambooth_shared.dreambooth_models_path
    setattr(dreambooth_shared, 'dreambooth_models_path', base_model_folder)
    save_config(model_name)
    setattr(dreambooth_shared, 'dreambooth_models_path', origin_model_path)


def cloud_train(
        local_model_name: str,
        train_model_name: str,
        db_use_txt2img=False,
        training_instance_type: str= "",
        creator: str = ""
):
    integral_check = False
    job_id = ""

    url = get_variable_from_json('api_gateway_url')
    api_key = get_variable_from_json('api_token')
    if url is None or api_key is None:
        logger.debug("Url or API-Key is not setting.")
        return
    url += "trainings"
    try:
        # Get data path and class data path.
        print(f"Start cloud training {train_model_name}")
        db_config_path = os.path.join(f"models/dreambooth/{local_model_name}/db_config.json")
        with open(db_config_path) as db_config_file:
            config = json.load(db_config_file)
        local_data_path_list = []
        local_class_data_path_list = []
        data_path_list = []
        class_data_path_list = []
        for concept in config["concepts_list"]:
            local_data_path_list.append(concept["instance_data_dir"])
            local_class_data_path_list.append(concept["class_data_dir"])
            data_path_list.append(concept["instance_data_dir"].replace("s3://", "").replace("/", "-").strip("-"))
            class_data_path_list.append(concept["class_data_dir"].replace("s3://", "").replace("/", "-").strip("-"))
        model_list = get_cloud_db_models(username=creator)
        new_db_config_path = os.path.join(base_model_folder, f"{train_model_name}/db_config_cloud.json")
        print(f"hack config from {local_model_name} to {new_db_config_path}")
        hack_db_config(config, new_db_config_path, train_model_name, data_path_list, class_data_path_list, local_model_name)
        if config["save_lora_for_extra_net"] == True:
            model_type = "Lora"
        else:
            model_type = "Stable-diffusion"

        # db_config_path = f"models/dreambooth/{model_name}/db_config.json"
        # os.makedirs(os.path.dirname(db_config_path), exist_ok=True)
        # os.system(f"cp {dummy_db_config_path} {db_config_path}")
        for model in model_list:
            if model["name"] == train_model_name:
                model_id = model["id"]
                model_s3_path = model["output_s3_location"]
                break

        response = async_prepare_for_training_on_sagemaker(
            model_id, train_model_name, model_s3_path, local_data_path_list, local_class_data_path_list,
            new_db_config_path, model_type, training_instance_type, creator)
        job_id = response['data']["training"]["id"]

        payload = {
            "status": "Training"
        }
        response = requests.put(url=f"{url}/{job_id}/start", json=payload, headers={'x-api-key': api_key})
        response.raise_for_status()
        print(f"Start training response:\n{response.json()}")
        integral_check = True
    except Exception as e:
        gr.Error(f'train job {train_model_name} failed: {str(e)}')
    finally:
        if not integral_check:
            if job_id:
                gr.Error(f'train job {train_model_name} failed')
                response = requests.put(url=f"{url}/{job_id}/stop", headers={'x-api-key': api_key})
                print(f'training job failed but updated the job status {response.json()}')


def async_cloud_train(db_model_name,
                      cloud_db_model_name,
                      db_use_txt2img,
                      cloud_train_instance_type,
                      pr: gr.Request
                      ):
    upload_thread = threading.Thread(target=cloud_train,
                                     args=(db_model_name,
                                           cloud_db_model_name,
                                           db_use_txt2img,
                                           cloud_train_instance_type,
                                           pr.username
                                           ))
    upload_thread.start()
    train_job_list = get_train_job_list(pr)
    train_job_list.insert(0, ['', db_model_name, 'Initialed at Local', ''])
    return train_job_list


def get_train_job_list(pr: gr.Request):
    # Start creating model on cloud.
    url = get_variable_from_json('api_gateway_url')
    api_key = get_variable_from_json('api_token')
    if not url or not api_key:
        logger.debug("Url or API-Key is not setting.")
        return []

    table = []
    try:
        url += "trainings?types=Stable-diffusion&types=Lora"
        encode_type = "utf-8"
        response = requests.get(url=url, headers={
            'x-api-key': api_key,
            'Authorization': f'Bearer {base64.b16encode(pr.username.encode(encode_type)).decode(encode_type)}',
        }).json()
        logger.info(f"trainings response: {response}")
        if 'items' in response['data'] and response['data']['items']:
            train_jobs = response['data']['items']
            train_jobs.sort(key=lambda t: t['created'] if 'created' in t else sys.float_info.max, reverse=True)
            for trainJob in train_jobs:
                table.append([
                    trainJob['id'][:6],
                    trainJob['model_name'],
                    trainJob["status"],
                    trainJob['sagemaker_train_name']
                ])
    except requests.exceptions.RequestException as e:
        print(f"exception {e}")

    return table


def get_sorted_cloud_dataset(username):
    url = get_variable_from_json('api_gateway_url') + 'datasets?dataset_status=Enabled'
    api_key = get_variable_from_json('api_token')
    if not url or not api_key:
        logger.debug("Url or API-Key is not setting.")
        return []

    try:
        encode_type = "utf-8"
        raw_response = requests.get(url=url, headers={
            'x-api-key': api_key,
            'Authorization': f'Bearer {base64.b16encode(username.encode(encode_type)).decode(encode_type)}',
        })
        raw_response.raise_for_status()
        response = raw_response.json()
        logger.info(f"datasets response: {response}")
        datasets = response['data']['items']
        datasets.sort(key=lambda t: t['timestamp'] if 'timestamp' in t else sys.float_info.max, reverse=True)
        return datasets
    except Exception as e:
        logger.error(f"exception {e}")
        return []


def wrap_load_params(self, params_dict):
    for key, value in params_dict.items():
        if hasattr(self, key):
            setattr(self, key, value)
    if self.instance_data_dir:
        if self.instance_data_dir.startswith("s3://"):
            self.is_valid = True
        else:
            self.is_valid = os.path.isdir(self.instance_data_dir)
        if not self.is_valid:
            print(f"Invalid Dataset Directory: {self.instance_data_dir}")


Concept.load_params = wrap_load_params
