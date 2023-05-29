#import sagemaker
import re
import time
import math
import json
import threading
import requests
import copy
import os
import logging
import gradio as gr
import modules.scripts as scripts
from modules import shared, devices, script_callbacks, processing, masking, images, sd_models
from modules.ui import create_refresh_button
from utils import upload_file_to_s3_by_presign_url, upload_multipart_files_to_s3_by_signed_url
from utils import get_variable_from_json
from utils import save_variable_to_json

import sys
import pickle
import html

# TODO: Automaticly append the dependent module path.
sys.path.append("extensions/sd_dreambooth_extension")
sys.path.append("extensions/stable-diffusion-aws-extension")
sys.path.append("extensions/stable-diffusion-aws-extension/scripts")
# TODO: Do not use the dreambooth status module.
from dreambooth.shared import status
from dreambooth import shared as dreambooth_shared
# from extensions.sd_dreambooth_extension.scripts.main import get_sd_models
from dreambooth.ui_functions import load_model_params, load_params
from dreambooth.dataclasses.db_config import save_config, from_file
from urllib.parse import urljoin
import sagemaker_ui

job_link_list = []
ckpt_dict = {}
base_model_folder = "models/sagemaker_dreambooth/"

def get_cloud_db_models(types="Stable-diffusion", status="Complete"):
    try:
        api_gateway_url = get_variable_from_json('api_gateway_url')
        if api_gateway_url is None:
            print(f"failed to get the api_gateway_url, can not fetch date from remote")
            return []
        url = f"{api_gateway_url}models?"
        if types:
            url = f"{url}types={types}&"
        if status:
            url = f"{url}status={status}&"
        url = url.strip("&")
        response = requests.get(url=url, headers={'x-api-key': get_variable_from_json('api_token')}).json()
        model_list = []
        if "models" not in response:
            return []
        for model in response["models"]:
            model_list.append(model)
            params = model['params']
            if 'resp' in params:
                db_config = params['resp']['config_dict']
                # TODO:
                model_dir = f"{base_model_folder}/{model['model_name']}"
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
        print('Failed to get cloud models.')
        print(e)
        return []

def get_cloud_ckpts():
    try:
        api_gateway_url = get_variable_from_json('api_gateway_url')
        if api_gateway_url is None:
            print(f"failed to get the api_gateway_url, can not fetch date from remote")
            return []

        url = api_gateway_url + "checkpoints?status=Active&types=Stable-diffusion"
        response = requests.get(url=url, headers={'x-api-key': get_variable_from_json('api_token')}).json()
        if "checkpoints" not in response:
            return []
        global ckpt_dict
        for ckpt in response["checkpoints"]:
            # Only get ckpts whose name is not empty.
            if len(ckpt['name']) > 0:
                ckpt_key = f"cloud-{ckpt['name'][0]}-{ckpt['id']}"
                ckpt_dict[ckpt_key] = ckpt
    except Exception as e:
        print(e)
        return []

def get_cloud_ckpt_name_list():
    get_cloud_ckpts()
    return ckpt_dict.keys()

def get_cloud_db_model_name_list():
    model_list = get_cloud_db_models()
    if model_list is None:
        model_name_list = []
    else:
        model_name_list = [model['model_name'] for model in model_list]
    return model_name_list

# get local and cloud checkpoints.
def get_sd_cloud_models():
    sd_models.list_models()
    local_sd_list = sd_models.checkpoints_list
    names = []
    for key in local_sd_list:
        names.append(f"local-{key}")
    names += get_cloud_ckpt_name_list()
    return names

def hack_db_config(db_config, db_config_file_path, model_name, data_tar_list, class_data_tar_list):
    for k in db_config:
        if k == "model_dir":
            db_config[k] = re.sub(".+/(models/dreambooth/).+$", f"\\1{model_name}", db_config[k])
        elif k == "pretrained_model_name_or_path":
            db_config[k] = re.sub(".+/(models/dreambooth/).+(working)$", f"\\1{model_name}/\\2", db_config[k])
        elif k == "model_name":
            db_config[k] = db_config[k].replace("dummy_local_model", model_name)
        elif k == "concepts_list":
            for concept, data_tar, class_data_tar in zip(db_config[k], data_tar_list, class_data_tar_list):
                if len(data_tar) > 0:
                    concept["instance_data_dir"] = os.path.basename(re.sub("\.tar$", "", data_tar))
                else:
                    concept["instance_data_dir"] = ""
                if len(class_data_tar) > 0:
                    concept["class_data_dir"] = os.path.basename(re.sub("\.tar$", "", class_data_tar))
                else:
                    concept["class_data_dir"] = ""
        # else:
        #     db_config[k] = db_config[k].replace("dummy_local_model", model_name)
    with open(db_config_file_path, "w") as db_config_file_w:
        json.dump(db_config, db_config_file_w)

def async_prepare_for_training_on_sagemaker(
        model_id: str,
        model_name: str,
        s3_model_path: str,
        data_path_list: list,
        class_data_path_list: list,
        db_config_path: str,
):
    url = get_variable_from_json('api_gateway_url')
    api_key = get_variable_from_json('api_token')
    if url is None or api_key is None:
        logging.error("Url or API-Key is not setting.")
        return
    url += "train"
    upload_files = []
    db_config_tar = f"db_config.tar"
    os.system(f"tar cvf {db_config_tar} {db_config_path}")
    upload_files.append(db_config_tar)
    data_tar_list = []
    for data_path in data_path_list:
        if len(data_path) == 0:
            data_tar_list.append("")
            continue
        data_tar = f'data-{data_path.replace("/", "-")}.tar'
        data_tar_list.append(data_tar)
        print("Pack the data file.")
        os.system(f"tar cvf {data_tar} {data_path}")
        upload_files.append(data_tar)
    class_data_tar_list = []
    for class_data_path in class_data_path_list:
        if len(class_data_path) == 0:
            class_data_tar_list.append("")
            continue
        class_data_tar = f'class-data-{class_data_path.replace("/", "-")}.tar'
        class_data_tar_list.append(class_data_tar)
        upload_files.append(class_data_tar)
        print("Pack the class data file.")
        os.system(f"tar cvf {class_data_tar} {class_data_path}")
    payload = {
        "train_type": "Stable-diffusion",
        "model_id": model_id,
        "filenames": upload_files,
        "params": {
            "training_params": {
                "s3_model_path": s3_model_path,
                "model_name": model_name,
                "data_tar_list": data_tar_list,
                "class_data_tar_list": class_data_tar_list,
            }
        }
    }
    print("Post request for upload s3 presign url.")
    response = requests.post(url=url, json=payload, headers={'x-api-key': api_key})
    json_response = response.json()
    for local_tar_path, s3_presigned_url in response.json()["s3PresignUrl"].items():
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

def async_create_model_on_sagemaker(
        new_model_name: str,
        ckpt_path: str,
        from_hub=False,
        new_model_url="",
        new_model_token="",
        extract_ema=False,
        train_unfrozen=False,
        is_512=True,
):
    params = copy.deepcopy(locals())
    if len(params["ckpt_path"]) == 0 or len(params["new_model_name"]) == 0:
        logging.error("ckpt_path or model_name is not setting.")
        return
    if re.match("^[a-zA-Z0-9](-*[a-zA-Z0-9]){0,30}$", params["new_model_name"]) is None:
        logging.error("model_name is not match pattern.")
        return
    ckpt_key = ckpt_path
    url = get_variable_from_json('api_gateway_url')
    api_key = get_variable_from_json('api_token')
    if url is None or api_key is None:
        logging.error("Url or API-Key is not setting.")
        return
    url += "model"
    if params["ckpt_path"].startswith("cloud-"):
        if params["ckpt_path"] not in ckpt_dict:
            logging.error("Cloud checkpoint is not exist.")
            return
        ckpt_name_list = ckpt_dict[ckpt_key]["name"]
        if len(ckpt_name_list) == 0:
            logging.error("Checkpoint name error.")
            return
        params["ckpt_path"] = ckpt_name_list[0].rstrip(".tar")
        ckpt_info = ckpt_dict[ckpt_key]
        payload = {
            "model_type": "Stable-diffusion",
            "name": new_model_name,
            "checkpoint_id": ckpt_info["id"],
            "filenames": [],
            "params": {
                "ckpt_from_cloud": True,
                "s3_ckpt_path": ckpt_dict[ckpt_key]["s3Location"],
                "create_model_params": params
            }
        }
        print("Post request for upload s3 presign url.")
        response = requests.post(url=url, json=payload, headers={'x-api-key': api_key})
        json_response = response.json()
        model_id = json_response["job"]["id"]
        payload = {
            "model_id": model_id,
            "status": "Creating",
            "multi_parts_tags": {}
        }
    elif params["ckpt_path"].startswith("local-"):
        # The ckpt path has a hash suffix?
        params["ckpt_path"] = " ".join(params["ckpt_path"].split(" ")[:1])
        params["ckpt_path"] = params["ckpt_path"].lstrip("local-")
        # Prepare for creating model on cloud.
        local_model_path = f'models/Stable-diffusion/{params["ckpt_path"]}'
        local_tar_path = f'{params["ckpt_path"]}.tar'

        part_size = 1000 * 1024 * 1024
        file_size = os.stat(local_model_path)
        parts_number = math.ceil(file_size.st_size/part_size)

        payload = {
            "model_type": "Stable-diffusion",
            "name": new_model_name,
            "filenames": [{
                "filename": local_tar_path,
                "parts_number": parts_number
            }],
            "params": {"create_model_params": params}
        }
        print("Post request for upload s3 presign url.")
        response = requests.post(url=url, json=payload, headers={'x-api-key': api_key})
        json_response = response.json()
        model_id = json_response["job"]["id"]
        multiparts_tags=[]
        if not from_hub:
            print("Pack the model file.")
            os.system(f"tar cvf {local_tar_path} {local_model_path}")
            s3_base = json_response["job"]["s3_base"]
            print(f"Upload to S3 {s3_base}")
            print(f"Model ID: {model_id}")
            # Upload src model to S3.
            s3_signed_urls_resp = response.json()["s3PresignUrl"][local_tar_path]
            multiparts_tags = upload_multipart_files_to_s3_by_signed_url(
                local_tar_path,
                s3_signed_urls_resp,
                part_size
            )
            payload = {
                "model_id": model_id,
                "status": "Creating",
                "multi_parts_tags": {local_tar_path: multiparts_tags}
            }
    else:
        logging.error("Create model params error.")
        return
    # Start creating model on cloud.
    response = requests.put(url=url, json=payload, headers={'x-api-key': api_key})
    print(response)

def cloud_create_model(
        new_model_name: str,
        ckpt_path: str,
        from_hub=False,
        new_model_url="",
        new_model_token="",
        extract_ema=False,
        train_unfrozen=False,
        is_512=True,
):
    upload_thread = threading.Thread(target=async_create_model_on_sagemaker,
                                     args=(new_model_name, ckpt_path, from_hub, new_model_url, new_model_token, extract_ema, train_unfrozen, is_512))
    upload_thread.start()

def cloud_train(
        train_model_name: str,
        local_model_name=False
):
    # Get data path and class data path.
    print(f"Start cloud training {train_model_name}")
    config = wrap_get_local_config("dummy_local_model")
    data_path_list = []
    class_data_path_list = []
    for concept in config.concepts_list:
        data_path_list.append(concept["instance_data_dir"])
        class_data_path_list.append(concept["class_data_dir"])
    model_list = get_cloud_db_models()
    db_config_path = "models/dreambooth/dummy_local_model/db_config.json"
    with open(db_config_path) as db_config_file:
        db_config = json.load(db_config_file)
    new_db_config_path = os.path.join(base_model_folder, f"{train_model_name}/db_config.json")
    hack_db_config(db_config, new_db_config_path, model_name, data_path_list, class_data_path_list)

    # db_config_path = f"models/dreambooth/{model_name}/db_config.json"
    # os.makedirs(os.path.dirname(db_config_path), exist_ok=True)
    # os.system(f"cp {dummy_db_config_path} {db_config_path}")
    for model in model_list:
        model_id = model["id"]
        model_name = model["model_name"]
        model_s3_path = model["output_s3_location"]
        if model_name == train_model_name:
            # upload_thread = threading.Thread(target=async_prepare_for_training_on_sagemaker,
            #                                 args=(model_id, model_name, s3_model_path,data_path, class_data_path))
            # upload_thread.start()
            response = async_prepare_for_training_on_sagemaker(
                model_id, model_name, model_s3_path, data_path_list, class_data_path_list, new_db_config_path)
            job_id = response["job"]["id"]
            url = get_variable_from_json('api_gateway_url')
            api_key = get_variable_from_json('api_token')
            if url is None or api_key is None:
                logging.error("Url or API-Key is not setting.")
                break
            url += "train"
            payload = {
                "train_job_id": job_id,
                "status": "Training"
            }
            # Start creating model on cloud.
            url = get_variable_from_json('api_gateway_url')
            api_key = get_variable_from_json('api_token')
            if url is None or api_key is None:
                logging.error("Url or API-Key is not setting.")
                break
            url += "train"
            payload = {
                "train_job_id": job_id,
                "status": "Training"
            }
            # Start creating model on cloud.
            response = requests.put(url=url, json=payload, headers={'x-api-key': api_key}).json()
            print(f"Start training response:\n{response}")


def get_train_job_list():
    # Start creating model on cloud.
    url = get_variable_from_json('api_gateway_url')
    api_key = get_variable_from_json('api_token')
    if not url or not api_key:
        logging.error("Url or API-Key is not setting.")
        return []

    table = []
    try:
        url += "trains?types=Stable-diffusion"
        response = requests.get(url=url, headers={'x-api-key': api_key}).json()
        response['trainJobs'].sort(key=lambda t:t['created'] if 'created' in t else sys.float_info.max, reverse=True)
        for trainJob in response['trainJobs']:
            table.append([trainJob['id'][:6], trainJob['modelName'], trainJob["status"], trainJob['sagemakerTrainName']])
    except requests.exceptions.RequestException as e:
        print(f"exception {e}")

    return table


def get_create_model_job_list():
    # Start creating model on cloud.
    url = get_variable_from_json('api_gateway_url')
    api_key = get_variable_from_json('api_token')
    if not url or not api_key:
        logging.error("Url or API-Key is not setting.")
        return []

    table = []
    try:
        url += "models?types=Stable-diffusion"
        response = requests.get(url=url, headers={'x-api-key': api_key}).json()
        response['models'].sort(key=lambda t:t['created'] if 'created' in t else sys.float_info.max, reverse=True)
        for model in response['models']:
            table.append([model['id'][:6], model['model_name'], model["status"]])
    except requests.exceptions.RequestException as e:
        print(f"exception {e}")

    return table
