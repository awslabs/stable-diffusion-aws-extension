#import sagemaker
import re
import math
import threading
import requests
import copy
import os
import sys
import logging
from modules import sd_models
from utils import upload_multipart_files_to_s3_by_signed_url
from utils import get_variable_from_json

job_link_list = []
ckpt_dict = {}
base_model_folder = "models/sagemaker_dreambooth/"

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

# get local and cloud checkpoints.
def get_sd_cloud_models():
    sd_models.list_models()
    local_sd_list = sd_models.checkpoints_list
    names = []
    for key in local_sd_list:
        names.append(f"local-{key}")
    names += get_cloud_ckpt_name_list()
    return names

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
                "s3_ckpt_path": os.path.join(ckpt_dict[ckpt_key]["s3Location"], ckpt_name_list[0]),
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
