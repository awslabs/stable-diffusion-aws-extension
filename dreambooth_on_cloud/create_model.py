import base64
import json
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
from utils import tar, has_config
import gradio as gr

logging.basicConfig(filename='sd-aws-ext.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

job_link_list = []
ckpt_dict = {}
base_model_folder = "models/sagemaker_dreambooth/"


def get_cloud_ckpts():
    global ckpt_dict
    ckpt_dict = {}
    try:
        api_gateway_url = get_variable_from_json('api_gateway_url')
        if not has_config():
            print(f"failed to get the api_gateway_url, can not fetch date from remote")
            return []

        url = api_gateway_url + "checkpoints?status=Active"
        response = requests.get(url=url, headers={'x-api-key': get_variable_from_json('api_token')}).json()
        if "checkpoints" not in response:
            return []
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
        shared_src: str,
        from_hub=False,
        new_model_url="",
        new_model_token="",
        extract_ema=False,
        train_unfrozen=False,
        is_512=True,
        creator=""
):
    params = copy.deepcopy(locals())
    del params['creator']
    integral_check = False
    url = get_variable_from_json('api_gateway_url')
    api_key = get_variable_from_json('api_token')

    if not has_config():
        logger.debug("Url or API-Key is not setting.")
        return
    url += "models"
    model_id = ""
    try:
        if len(params["ckpt_path"]) == 0 or len(params["new_model_name"]) == 0:
            logger.debug("ckpt_path or model_name is not setting.")
            return
        if re.match("^[a-zA-Z0-9](-*[a-zA-Z0-9]){0,30}$", params["new_model_name"]) is None:
            logger.debug("model_name is not match pattern.")
            return
        ckpt_key = ckpt_path
        if params["ckpt_path"].startswith("cloud-"):
            if params["ckpt_path"] not in ckpt_dict:
                logger.debug("Cloud checkpoint is not exist.")
                return
            ckpt_name_list = ckpt_dict[ckpt_key]["name"]
            if len(ckpt_name_list) == 0:
                logger.debug("Checkpoint name error.")
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
                    "s3_ckpt_path": f'{ckpt_dict[ckpt_key]["s3Location"]}/{ckpt_name_list[0]}',
                    "create_model_params": params,
                },
                "creator": creator,
            }
            print("Post request for upload s3 presign url.")
            response = requests.post(url=url, json=payload, headers={'x-api-key': api_key})

            print(response.json())

            response.raise_for_status()

            json_response = response.json()['data']
            model_id = json_response["model"]["id"]
            payload = {
                "status": "Creating",
                "multi_parts_tags": {}
            }
        elif params["ckpt_path"].startswith("local-"):
            # The ckpt path has a hash suffix?
            params["ckpt_path"] = " ".join(params["ckpt_path"].split(" ")[:1])
            params["ckpt_path"] = params["ckpt_path"].lstrip("local-")
            # Prepare for creating model on the cloud.
            local_model_path = f'models/Stable-diffusion/{params["ckpt_path"]}'
            local_tar_path = f'{params["ckpt_path"]}'

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
                "params": {"create_model_params": params},
                "creator": creator,
            }
            print('Post request for upload s3 presign url.')
            response = requests.post(url=url, json=payload, headers={'x-api-key': api_key})

            print(json.dumps(response.json(), indent=4))

            response.raise_for_status()

            json_response = response.json()['data']
            model_id = json_response["model"]["id"]
            multiparts_tags=[]
            if not from_hub:
                print("Pack the model file.")
                # os.system(f"tar cvf {local_tar_path} {local_model_path}")
                tar(mode='c', archive=local_tar_path, sfiles=[local_model_path], verbose=True)
                s3_base = json_response["model"]["s3_location"]
                print(f"Upload to S3 {s3_base}")
                print(f"Model ID: {model_id}")
                # Upload src model to S3.
                s3_signed_urls_resp = json_response["s3PresignUrl"][local_tar_path]
                multiparts_tags = upload_multipart_files_to_s3_by_signed_url(
                    local_tar_path,
                    s3_signed_urls_resp,
                    part_size
                )
                payload = {
                    "status": "Creating",
                    "multi_parts_tags": {local_tar_path: multiparts_tags}
                }
        else:
            logger.debug("Create model params error.")
            return
        # Start creating model on cloud.
        response = requests.put(url=f"{url}/{model_id}", json=payload, headers={'x-api-key': api_key})
        integral_check = True
        print(response)
    except Exception as e:
        print(e)
        gr.Error(f'model {new_model_name} failed, please try again')
    finally:
        if not integral_check:
            if model_id:
                payload = {
                    "status": "Fail",
                    "multi_parts_tags": {local_tar_path: []}
                }
                response = requests.put(url=f"{url}/{model_id}", json=payload, headers={'x-api-key': api_key})
                print(response)
            else:
                gr.Error(f'model {new_model_name} not created, please try again')


local_job_cache = {
    'create_model': {},
}


def cloud_create_model(
        new_model_name: str,
        ckpt_path: str,
        shared_src: str,
        from_hub,
        new_model_url,
        new_model_token,
        extract_ema,
        train_unfrozen,
        is_512,
        pr: gr.Request
):

    upload_thread = threading.Thread(target=async_create_model_on_sagemaker,
                                     args=(new_model_name, ckpt_path, shared_src, from_hub, new_model_url, new_model_token, extract_ema, train_unfrozen, is_512, pr.username))
    upload_thread.start()

    dashboard_list = get_create_model_job_list(pr)
    dashboard_list.insert(0, ['', new_model_name, 'Initialed at Local'])
    global local_job_cache
    local_job_cache[new_model_name]='created'

    return dashboard_list


def get_create_model_job_list(pr: gr.Request):
    # Start creating model on cloud.
    url = get_variable_from_json('api_gateway_url')
    api_key = get_variable_from_json('api_token')
    if not url or not api_key:
        logger.debug("Url or API-Key is not setting.")
        return []

    global local_job_cache
    dashboard_list = []
    try:
        url += "models?types=Stable-diffusion"
        encode_type = "utf-8"
        response = requests.get(url=url, headers={
            'x-api-key': api_key,
            'Authorization': f'Bearer {base64.b16encode(pr.username.encode(encode_type)).decode(encode_type)}'
        }).json()

        response['data']['items'].sort(key=lambda t: t['created'] if 'created' in t else sys.float_info.max, reverse=True)
        for model in response['data']['items']:
            if model['name'] in local_job_cache['create_model']:
                del local_job_cache['create_model'][model['name']]

            dashboard_list.append([model['id'][:6], model['name'], model["status"]])

        if local_job_cache is not None and len(local_job_cache['create_model']) > 0:
            dashboard_list = [['', item, 'Initialed at Local'] for item in local_job_cache['create_model']] + dashboard_list
    except Exception as e:
        print(f"exception {e}")
        return []

    return dashboard_list
