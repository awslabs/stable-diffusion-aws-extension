import re
import json
import requests
import os
import sys
import logging
from utils import upload_file_to_s3_by_presign_url
from utils import get_variable_from_json

# TODO: Automaticly append the dependent module path.
sys.path.append("extensions/sd_dreambooth_extension")
# TODO: Do not use the dreambooth status module.
from dreambooth import shared as dreambooth_shared
# from extensions.sd_dreambooth_extension.scripts.main import get_sd_models
from dreambooth.ui_functions import load_model_params
from dreambooth.dataclasses.db_config import save_config, from_file
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

def get_cloud_db_model_name_list():
    model_list = get_cloud_db_models()
    if model_list is None:
        model_name_list = []
    else:
        model_name_list = [model['model_name'] for model in model_list]
    return model_name_list

def hack_db_config(db_config, db_config_file_path, model_name, data_list, class_data_list):
    for k in db_config:
        if k == "model_dir":
            db_config[k] = re.sub(".+/(models/dreambooth/).+$", f"\\1{model_name}", db_config[k])
        elif k == "pretrained_model_name_or_path":
            db_config[k] = re.sub(".+/(models/dreambooth/).+(working)$", f"\\1{model_name}/\\2", db_config[k])
        elif k == "model_name":
            db_config[k] = db_config[k].replace("dummy_local_model", model_name)
        elif k == "concepts_list":
            for concept, data, class_data in zip(db_config[k], data_list, class_data_list):
                concept["instance_data_dir"] = data
                concept["class_data_dir"] = class_data
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
        model_type: str,
        training_instance_type: str
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
        data_tar = f'data-{data_path.replace("/", "-").strip("-")}.tar'
        data_tar_list.append(data_tar)
        print("Pack the data file.")
        os.system(f"tar cf {data_tar} {data_path}")
        upload_files.append(data_tar)
    class_data_tar_list = []
    for class_data_path in class_data_path_list:
        if len(class_data_path) == 0:
            class_data_tar_list.append("")
            continue
        class_data_tar = f'class-data-{class_data_path.replace("/", "-").strip("-")}.tar'
        class_data_tar_list.append(class_data_tar)
        upload_files.append(class_data_tar)
        print("Pack the class data file.")
        os.system(f"tar cf {class_data_tar} {class_data_path}")
    payload = {
        "train_type": model_type,
        "model_id": model_id,
        "filenames": upload_files,
        "params": {
            "training_params": {
                "s3_model_path": s3_model_path,
                "model_name": model_name,
                "data_tar_list": data_tar_list,
                "class_data_tar_list": class_data_tar_list,
                "training_instance_type": training_instance_type
            }
        }
    }
    print("Post request for upload s3 presign url.")
    response = requests.post(url=url, json=payload, headers={'x-api-key': api_key})
    json_response = response.json()
    print(json_response)
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

def cloud_train(
        train_model_name: str,
        local_model_name=False,
        training_instance_type: str= ""
):
    # Get data path and class data path.
    print(f"Start cloud training {train_model_name}")
    db_config_path = os.path.join("models/dreambooth/dummy_local_model/db_config.json")
    with open(db_config_path) as db_config_file:
        config = json.load(db_config_file)
    local_data_path_list = []
    local_class_data_path_list = []
    data_path_list = []
    class_data_path_list = []
    for concept in config["concepts_list"]:
        local_data_path_list.append(concept["instance_data_dir"])
        local_class_data_path_list.append(concept["class_data_dir"])
        data_path_list.append(concept["instance_data_dir"].replace("/", "-").strip("-"))
        class_data_path_list.append(concept["class_data_dir"].replace("/", "-").strip("-"))
    model_list = get_cloud_db_models()
    new_db_config_path = os.path.join(base_model_folder, f"{train_model_name}/db_config_cloud.json")
    hack_db_config(config, new_db_config_path, train_model_name, data_path_list, class_data_path_list)
    if config["use_lora"] == True:
        model_type = "Lora"
    else:
        model_type = "Stable-diffusion"

    # db_config_path = f"models/dreambooth/{model_name}/db_config.json"
    # os.makedirs(os.path.dirname(db_config_path), exist_ok=True)
    # os.system(f"cp {dummy_db_config_path} {db_config_path}")
    for model in model_list:
        if model["model_name"] == train_model_name:
            model_id = model["id"]
            model_s3_path = model["output_s3_location"]
            break
    # upload_thread = threading.Thread(target=async_prepare_for_training_on_sagemaker,
    #                                 args=(model_id, model_name, s3_model_path,data_path, class_data_path))
    # upload_thread.start()
    response = async_prepare_for_training_on_sagemaker(
        model_id, train_model_name, model_s3_path, local_data_path_list, local_class_data_path_list,
        new_db_config_path, model_type, training_instance_type)
    job_id = response["job"]["id"]
    url = get_variable_from_json('api_gateway_url')
    api_key = get_variable_from_json('api_token')
    if url is None or api_key is None:
        logging.error("Url or API-Key is not setting.")
        return
    url += "train"
    payload = {
        "train_job_id": job_id,
        "status": "Training"
    }
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


def get_sorted_cloud_dataset():
    url = get_variable_from_json('api_gateway_url') + 'datasets?dataset_status=Enabled'
    api_key = get_variable_from_json('api_token')
    if not url or not api_key:
        logging.error("Url or API-Key is not setting.")
        return []

    try:
        raw_response = requests.get(url=url, headers={'x-api-key': api_key})
        raw_response.raise_for_status()
        response = raw_response.json()
        response['datasets'].sort(key=lambda t:t['timestamp'] if 'timestamp' in t else sys.float_info.max, reverse=True)
        return response['datasets']
    except Exception as e:
        print(f"exception {e}")
        return []



