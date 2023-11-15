import copy
import itertools
import logging
import os
from pathlib import Path
import html
import boto3
import time

import json

import gradio
import requests
import base64
from urllib.parse import urljoin

import gradio as gr

import utils
from aws_extension.auth_service.simple_cloud_auth import cloud_auth_manager
from aws_extension.cloud_api_manager.api_manager import api_manager
from aws_extension.sagemaker_ui_utils import create_refresh_button_by_user

from modules import shared, scripts
from modules.ui import create_refresh_button
from modules.shared import opts
from modules.ui_components import FormRow, FormColumn, FormGroup, ToolButton, FormHTML
from utils import get_variable_from_json
from utils import upload_file_to_s3_by_presign_url, upload_multipart_files_to_s3_by_signed_url
from requests.exceptions import JSONDecodeError
from datetime import datetime
import math
import re

import asyncio
import nest_asyncio

from utils import cp, tar, rm

logger = logging.getLogger(__name__)
logger.setLevel(utils.LOGGING_LEVEL)

None_Option_For_On_Cloud_Model = "don't use on cloud inference"

inference_job_dropdown = None
textual_inversion_dropdown = None
hyperNetwork_dropdown = None
lora_dropdown = None
# sagemaker_endpoint = None
modelmerger_merge_on_cloud = None
interrogate_clip_on_cloud_button = None
interrogate_deep_booru_on_cloud_button = None

primary_model_name = None
secondary_model_name = None
tertiary_model_name = None

# TODO: convert to dynamically init the following variables
txt2img_inference_job_ids = []

sd_checkpoints = []
textual_inversion_list = []
lora_list = []
hyperNetwork_list = []
ControlNet_model_list = []

# Initial checkpoints information
checkpoint_info = {}
checkpoint_type = ["Stable-diffusion", "embeddings", "Lora", "hypernetworks", "ControlNet", "VAE"]
checkpoint_name = ["stable_diffusion", "embeddings", "lora", "hypernetworks", "controlnet", "VAE"]
stable_diffusion_list = []
embeddings_list = []

hypernetworks_list = []
controlnet_list = []
for ckpt_type, ckpt_name in zip(checkpoint_type, checkpoint_name):
    checkpoint_info[ckpt_type] = {}
# get api_gateway_url
api_gateway_url = get_variable_from_json('api_gateway_url')
api_key = get_variable_from_json('api_token')

start_time_picker_img_value = None
end_time_picker_img_value = None
start_time_picker_txt_value = None
end_time_picker_txt_value = None

txt_task_type = None
txt_status = None
txt_endpoint = None
txt_checkpoint = None

img_task_type = None
img_status = None
img_endpoint = None
img_checkpoint = None

show_all_inference_job = False

modelTypeMap = {
    'SD Checkpoints': 'Stable-diffusion',
    'Textual Inversion': 'embeddings',
    'LoRA model': 'Lora',
    'ControlNet model': 'ControlNet',
    'Hypernetwork': 'hypernetworks',
    'VAE': 'VAE'
}


def plaintext_to_html(text):
    text = "<p>" + "<br>\n".join([f"{html.escape(x)}" for x in text.split('\n')]) + "</p>"
    return text


def server_request_post(path, params):
    api_gateway_url = get_variable_from_json('api_gateway_url')
    # Check if api_url ends with '/', if not append it
    if not api_gateway_url.endswith('/'):
        api_gateway_url += '/'
    api_key = get_variable_from_json('api_token')
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    list_endpoint_url = f'{api_gateway_url}{path}'
    response = requests.post(list_endpoint_url, json=params, headers=headers)
    return response


def get_s3_file_names(bucket, folder):
    """Get a list of file names from an S3 bucket and folder."""
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket)
    objects = bucket.objects.filter(Prefix=folder)
    names = [obj.key for obj in objects]
    return names


def get_current_date():
    today = datetime.today()
    formatted_date = today.strftime('%Y-%m-%d')
    return formatted_date


def server_request(path):
    api_gateway_url = get_variable_from_json('api_gateway_url')
    # Check if api_url ends with '/', if not append it
    if not api_gateway_url.endswith('/'):
        api_gateway_url += '/'
    api_key = get_variable_from_json('api_token')
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    list_endpoint_url = f'{api_gateway_url}{path}'
    response = requests.get(list_endpoint_url, headers=headers)
    return response


def datetime_to_short_form(datetime_str):
    dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S.%f")
    short_form = dt.strftime("%Y-%m-%d-%H-%M-%S")
    return short_form


def query_page_inference_job_list(task_type: str, status: str, endpoint: str, checkpoint: str, is_img2img: bool,
                                  show_all: bool):
    global show_all_inference_job
    show_all_inference_job = show_all
    if is_img2img:
        global img_task_type
        img_task_type = task_type
        global img_status
        img_status = status
        global img_endpoint
        img_endpoint = endpoint
        global img_checkpoint
        img_checkpoint = checkpoint
        opt_type = 'img2img'
        logger.debug(f"{opt_type} {img_task_type} {img_status} {img_endpoint} {img_checkpoint} {show_all}")
        return query_inference_job_list(task_type, status, endpoint, checkpoint, opt_type)
    else:
        global txt_task_type
        txt_task_type = task_type
        global txt_status
        txt_status = txt_status
        global txt_endpoint
        txt_endpoint = endpoint
        global txt_checkpoint
        txt_checkpoint = checkpoint
        opt_type = 'txt2img'
        logger.debug(f"{opt_type} {txt_task_type} {txt_status} {txt_endpoint} {txt_checkpoint} {show_all}")
        return query_inference_job_list(task_type, status, endpoint, checkpoint, opt_type)


def query_img_inference_job_list(task_type: str, status: str, endpoint: str, checkpoint: str):
    opt_type = 'img2img'
    global img_task_type
    img_task_type = task_type
    global img_status
    img_status = status
    global img_endpoint
    img_endpoint = endpoint
    global img_checkpoint
    img_checkpoint = checkpoint
    return query_inference_job_list(task_type, status, endpoint, checkpoint, opt_type)


def query_txt_inference_job_list(task_type: str, status: str, endpoint: str, checkpoint: str):
    opt_type = 'txt2img'
    global txt_task_type
    txt_task_type = task_type
    global txt_status
    txt_status = status
    global txt_endpoint
    txt_endpoint = endpoint
    global txt_checkpoint
    txt_checkpoint = checkpoint

    return query_inference_job_list(task_type, status, endpoint, checkpoint, opt_type)


def query_inference_job_list(task_type: str = '', status: str = '',
                             endpoint: str = '', checkpoint: str = '', opt_type: str = ''):
    logger.debug(
        f"query_inference_job_list start！！{status},{task_type},{endpoint},{checkpoint},{start_time_picker_txt_value},{end_time_picker_txt_value} {show_all_inference_job}")
    try:
        body_params = {}
        if status:
            body_params['status'] = status
        if task_type:
            body_params['task_type'] = task_type
        if opt_type == 'txt2img':
            if start_time_picker_txt_value:
                body_params['start_time'] = start_time_picker_txt_value
            if end_time_picker_txt_value:
                body_params['end_time'] = end_time_picker_txt_value
        elif opt_type == 'img2img':
            if start_time_picker_img_value:
                body_params['start_time'] = start_time_picker_img_value
            if end_time_picker_img_value:
                body_params['end_time'] = end_time_picker_img_value
        if endpoint:
            endpoint_name_array = endpoint.split("+")
            if len(endpoint_name_array) > 0:
                body_params['endpoint'] = endpoint_name_array[0]
        if checkpoint:
            body_params['checkpoint'] = checkpoint
        body_params['limit'] = -1 if show_all_inference_job else 10
        response = server_request_post(f'inference/query-inference-jobs', body_params)
        r = response.json()
        logger.debug(r)
        if r:
            txt2img_inference_job_ids.clear()  # Clear the existing list before appending new values
            temp_list = []
            for obj in r:
                if obj.get('completeTime') is None:
                    complete_time = obj.get('startTime')
                else:
                    complete_time = obj.get('completeTime')
                status = obj.get('status')
                task_type = obj.get('taskType', 'txt2img')
                inference_job_id = obj.get('InferenceJobId')
                combined_string = f"{complete_time}-->{task_type}-->{status}-->{inference_job_id}"
                temp_list.append((complete_time, combined_string))
            # Sort the list based on completeTime in ascending order
            sorted_list = sorted(temp_list, key=lambda x: x[0], reverse=False)
            # Append the sorted combined strings to the txt2img_inference_job_ids list
            for item in sorted_list:
                txt2img_inference_job_ids.append(item[1])
            # inference_job_dropdown.update(choices=txt2img_inference_job_ids)
            return gr.Dropdown.update(choices=txt2img_inference_job_ids)
        else:
            logger.info("The API response is empty.")
            return gr.Dropdown.update(choices=[])
    except Exception as e:
        logger.error("Exception occurred when fetching inference_job_ids")
        logger.error(e)
        return gr.Dropdown.update(choices=[])


# def get_inference_job_list(txt2img_type_checkbox=True, img2img_type_checkbox=True, interrogate_type_checkbox=True):
#     global txt2img_inference_job_ids
#     try:
#         txt2img_inference_job_ids.clear()  # Clear the existing list before appending new values
#         response = server_request('inference/list-inference-jobs')
#         r = response.json()
#         logger.debug(f"response: {response.json()}")
#         filter_checkbox = False
#         selected_types = []
#         if txt2img_type_checkbox:
#             selected_types.append('txt2img')
#             filter_checkbox = True
#         if img2img_type_checkbox:
#             selected_types.append('img2img')
#             filter_checkbox = True
#         if interrogate_type_checkbox:
#             selected_types.append('interrogate_deepbooru')
#             filter_checkbox = True
#         logging.debug(f"selected_types: {selected_types}")
#         if r:
#             txt2img_inference_job_ids.clear()  # Clear the existing list before appending new values
#             temp_list = []
#             for obj in r:
#                 if obj.get('completeTime') is None:
#                     complete_time = obj.get('startTime')
#                 else:
#                     complete_time = obj.get('completeTime')
#                 status = obj.get('status')
#                 task_type = obj.get('taskType', 'txt2img')
#                 inference_job_id = obj.get('InferenceJobId')
#                 if filter_checkbox and task_type not in selected_types:
#                     continue
#                 combined_string = f"{complete_time}-->{task_type}-->{status}-->{inference_job_id}"
#                 temp_list.append((complete_time, combined_string))
#
#             # Sort the list based on completeTime in ascending order
#             sorted_list = sorted(temp_list, key=lambda x: x[0], reverse=False)
#
#             # Append the sorted combined strings to the txt2img_inference_job_ids list
#             for item in sorted_list:
#                 txt2img_inference_job_ids.append(item[1])
#             # inference_job_dropdown.update(choices=txt2img_inference_job_ids)
#             return gr.Dropdown.update(choices=txt2img_inference_job_ids)
#         else:
#             logger.debug("The API response is empty.")
#             return gr.Dropdown.update(choices=[])
#
#     except Exception as e:
#         logger.error("Exception occurred when fetching inference_job_ids")
#         return gr.Dropdown.update(choices=[])


def get_inference_job(inference_job_id):
    response = server_request(f'inference/get-inference-job?jobID={inference_job_id}')
    return response.json()


def get_inference_job_image_output(inference_job_id):
    try:
        response = server_request(f'inference/get-inference-job-image-output?jobID={inference_job_id}')
        r = response.json()
        txt2img_inference_job_image_list = []
        for obj in r:
            obj_value = str(obj)
            txt2img_inference_job_image_list.append(obj_value)
        return txt2img_inference_job_image_list
    except Exception as e:
        logger.error(f"An error occurred while getting inference job image output: {e}")
        return []


def get_inference_job_param_output(inference_job_id):
    try:
        response = server_request(f'inference/get-inference-job-param-output?jobID={inference_job_id}')
        r = response.json()
        txt2img_inference_job_param_list = []
        for obj in r:
            obj_value = str(obj)
            txt2img_inference_job_param_list.append(obj_value)
        return txt2img_inference_job_param_list
    except Exception as e:
        logger.error(f"An error occurred while getting inference job param output: {e}")
        return []


def download_images(image_urls: list, local_directory: str):
    if not os.path.exists(local_directory):
        os.makedirs(local_directory)

    image_list = []
    for url in image_urls:
        try:
            response = requests.get(url)
            response.raise_for_status()
            image_name = os.path.basename(url).split('?')[0]
            local_path = os.path.join(local_directory, image_name)

            with open(local_path, 'wb') as f:
                f.write(response.content)
            image_list.append(local_path)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading image {url}: {e}")
    return image_list


def get_model_list_by_type(model_type, username=""):
    api_gateway_url = get_variable_from_json('api_gateway_url')
    api_key = get_variable_from_json('api_token')

    # check if api_gateway_url and api_key are set
    if api_gateway_url is None or api_key is None:
        logger.info("api_gateway_url or api_key is not set")
        return []

    # Check if api_url ends with '/', if not append it
    if not api_gateway_url.endswith('/'):
        api_gateway_url += '/'

    url = api_gateway_url + f"checkpoints?status=Active"
    if isinstance(model_type, list):
        url += "&types=" + "&types=".join(model_type)
    else:
        url += f"&types={model_type}"

    try:
        encode_type = "utf-8"
        response = requests.get(url=url, headers={
            'x-api-key': api_key,
            'Authorization': f'Bearer {base64.b16encode(username.encode(encode_type)).decode(encode_type)}'
        })
        response.raise_for_status()
        json_response = response.json()

        if "checkpoints" not in json_response.keys():
            return []

        checkpoint_list = []
        for ckpt in json_response["checkpoints"]:
            if "name" not in ckpt:
                continue
            if ckpt["name"] is None:
                continue
            if ckpt["type"] is None:
                continue
            ckpt_type = ckpt["type"]
            for ckpt_name in ckpt["name"]:
                ckpt_s3_pos = f"{ckpt['s3Location']}/{ckpt_name}"
                checkpoint_info[ckpt_type][ckpt_name] = ckpt_s3_pos
                checkpoint_list.append(ckpt_name)

        unique_list = list(set(checkpoint_list))
        return unique_list
    except Exception as e:
        logger.error(f"Error fetching model list: {e}")
        return []


def get_checkpoints_by_type(model_type):
    url = "checkpoints?status=Active"
    if isinstance(model_type, list):
        url += "&types=" + "&types=".join(model_type)
    else:
        url += f"&types={model_type}"
    try:
        response = server_request(url)
        response.raise_for_status()
        json_response = response.json()
        if "checkpoints" not in json_response.keys():
            return []
        checkpoint_dict = {}
        for ckpt in json_response["checkpoints"]:
            if "name" not in ckpt:
                continue
            if ckpt["name"] is None:
                continue
            create_time = ckpt['created']
            created = datetime.fromtimestamp(create_time)
            for ckpt_name in ckpt["name"]:
                checkpoint = [ckpt_name, created]
                if ckpt_name not in checkpoint_dict:
                    checkpoint_dict[ckpt_name] = checkpoint
        checkpoint_list = list(checkpoint_dict.values())
        return checkpoint_list
    except Exception as e:
        logging.error(f"Error fetching checkpoints list: {e}")
        return []


def update_sd_checkpoints(username):
    model_type = ["Stable-diffusion"]
    return get_model_list_by_type(model_type)


def get_texual_inversion_list():
    model_type = "embeddings"
    return get_model_list_by_type(model_type)


def get_lora_list():
    model_type = "Lora"
    return get_model_list_by_type(model_type)


def get_hypernetwork_list():
    model_type = "hypernetworks"
    return get_model_list_by_type(model_type)


def get_controlnet_model_list():
    model_type = "ControlNet"
    return get_model_list_by_type(model_type)


def refresh_all_models(username):
    api_gateway_url = get_variable_from_json('api_gateway_url')
    api_key = get_variable_from_json('api_token')
    encode_type = "utf-8"

    try:
        for rp, name in zip(checkpoint_type, checkpoint_name):
            url = api_gateway_url + f"checkpoints?status=Active&types={rp}"
            response = requests.get(url=url, headers={
                'x-api-key': api_key,
                'Authorization': f'Bearer {base64.b16encode(username.encode(encode_type)).decode(encode_type)}',
            })
            json_response = response.json()
            logger.debug(f"response url json for model {rp} is {json_response}")
            checkpoint_info[rp] = {}
            if "checkpoints" not in json_response.keys():
                continue
            for ckpt in json_response["checkpoints"]:
                if "name" not in ckpt:
                    continue
                if ckpt["name"] is None:
                    continue
                ckpt_type = ckpt["type"]
                checkpoint_info[ckpt_type] = {}
                for ckpt_name in ckpt["name"]:
                    ckpt_s3_pos = f"{ckpt['s3Location']}/{ckpt_name.split(os.sep)[-1]}"
                    checkpoint_info[ckpt_type][ckpt_name] = ckpt_s3_pos
    except Exception as e:
        logger.error(f"Error refresh all models: {e}")


def sagemaker_upload_model_s3(sd_checkpoints_path, textual_inversion_path, lora_path, hypernetwork_path,
                              controlnet_model_path, vae_path, pr: gradio.Request):
    log = "start upload model to s3:"

    local_paths = [sd_checkpoints_path, textual_inversion_path, lora_path, hypernetwork_path, controlnet_model_path,
                   vae_path]

    logger.info(f"Refresh checkpoints before upload to get rid of duplicate uploads...")
    refresh_all_models(pr.username)

    for lp, rp in zip(local_paths, checkpoint_type):
        if lp == "" or not lp:
            continue
        logger.debug(f"lp is {lp}")
        model_name = lp.split(os.sep)[-1]

        exist_model_list = list(checkpoint_info[rp].keys())

        if model_name in exist_model_list:
            logger.info(f"!!!skip to upload duplicate model {model_name}")
            continue

        part_size = 1000 * 1024 * 1024
        file_size = os.stat(lp)
        parts_number = math.ceil(file_size.st_size / part_size)
        logger.info(f'!!!!!!!!!!{file_size} {parts_number}')

        # local_tar_path = f'{model_name}.tar'
        local_tar_path = model_name
        payload = {
            "checkpoint_type": rp,
            "filenames": [{
                "filename": local_tar_path,
                "parts_number": parts_number
            }],
            "params": {
                "message": "placeholder for chkpts upload test",
                "creator": pr.username
            }
        }
        api_gateway_url = get_variable_from_json('api_gateway_url')
        # Check if api_url ends with '/', if not append it
        if not api_gateway_url.endswith('/'):
            api_gateway_url += '/'
        api_key = get_variable_from_json('api_token')
        logger.info(f'!!!!!!api_gateway_url {api_gateway_url}')

        url = str(api_gateway_url) + "checkpoint"

        logger.debug(f"Post request for upload s3 presign url: {url}")

        response = requests.post(url=url, json=payload, headers={'x-api-key': api_key})

        try:
            response.raise_for_status()
            json_response = response.json()
            logger.debug(f"Response json {json_response}")
            s3_base = json_response["checkpoint"]["s3_location"]
            checkpoint_id = json_response["checkpoint"]["id"]
            logger.debug(f"Upload to S3 {s3_base}")
            logger.debug(f"Checkpoint ID: {checkpoint_id}")

            s3_signed_urls_resp = json_response["s3PresignUrl"][local_tar_path]
            # Upload src model to S3.
            if rp != "embeddings":
                local_model_path_in_repo = os.sep.join(['models', rp, model_name])
            else:
                local_model_path_in_repo = os.sep.join([rp, model_name])
            logger.debug("Pack the model file.")
            cp(lp, local_model_path_in_repo, recursive=True)
            if rp == "Stable-diffusion":
                model_yaml_name = model_name.split('.')[0] + ".yaml"
                local_model_yaml_path = os.sep.join([*lp.split(os.sep)[:-1], model_yaml_name])
                local_model_yaml_path_in_repo = os.sep.join(["models", rp, model_yaml_name])
                if os.path.isfile(local_model_yaml_path):
                    cp(local_model_yaml_path, local_model_yaml_path_in_repo, recursive=True)
                    tar(mode='c', archive=local_tar_path,
                        sfiles=[local_model_path_in_repo, local_model_yaml_path_in_repo], verbose=True)
                else:
                    tar(mode='c', archive=local_tar_path, sfiles=[local_model_path_in_repo], verbose=True)
            else:
                tar(mode='c', archive=local_tar_path, sfiles=[local_model_path_in_repo], verbose=True)

            multiparts_tags = upload_multipart_files_to_s3_by_signed_url(
                local_tar_path,
                s3_signed_urls_resp,
                part_size
            )

            payload = {
                "checkpoint_id": checkpoint_id,
                "status": "Active",
                "multi_parts_tags": {local_tar_path: multiparts_tags}
            }
            # Start creating model on cloud.
            response = requests.put(url=url, json=payload, headers={'x-api-key': api_key})
            s3_input_path = s3_base
            logger.debug(response)

            log = f"\n finish upload {local_tar_path} to {s3_base}"

            # os.system(f"rm {local_tar_path}")
            rm(local_tar_path, recursive=True)
        except Exception as e:
            logger.error(f"fail to upload model {lp}, error: {e}")

    logger.debug(f"Refresh checkpoints after upload...")
    refresh_all_models(pr.username)
    return log, None, None, None, None, None, None


def sagemaker_upload_model_s3_local():
    log = "Start upload:"
    return log


def sagemaker_upload_model_s3_url(model_type: str, url_list: str, params: str, pr: gradio.Request):
    model_type = modelTypeMap.get(model_type)
    if not model_type:
        return "Please choose the model type."
    url_pattern = r'(https?|ftp)://[^\s/$.?#].[^\s]*'
    if re.match(f'^{url_pattern}$', url_list):
        url_list = url_list.split(',')
    else:
        return "Please fill in right url list."
    if params:
        params_dict = json.loads(params)
    else:
        params_dict = {}

    params_dict['creator'] = pr.username
    body_params = {'checkpointType': model_type, 'modelUrl': url_list, 'params': params_dict}
    response = server_request_post('upload_checkpoint', body_params)
    response_data = response.json()
    logging.info(f"sagemaker_upload_model_s3_url response:{response_data}")
    log = "uploading……"
    if 'checkpoint' in response_data:
        if response_data['checkpoint'].get('status') == 'Active':
            log = "upload success!"
    return log


def generate_on_cloud(sagemaker_endpoint):
    logger.info(f"checkpiont_info {checkpoint_info}")
    logger.info(f"sagemaker endpoint {sagemaker_endpoint}")
    text = "failed to check endpoint"
    return plaintext_to_html(text)


# create a global event loop and apply the patch to allow nested event loops in single thread
loop = asyncio.get_event_loop()
nest_asyncio.apply()

MAX_RUNNING_LIMIT = 10


def async_loop_wrapper(f):
    global loop
    # check if there are any running or queued tasks inside the event loop
    if loop.is_running():
        # Calculate the number of running tasks
        while len([task for task in asyncio.all_tasks(loop) if not task.done()]) > MAX_RUNNING_LIMIT:
            logger.debug(f'Waiting for {MAX_RUNNING_LIMIT} running tasks to complete')
            time.sleep(1)
    else:
        # check if loop is closed and create a new one
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            # log this event since it should never happen
            logger.debug('Event loop was closed, created a new one')

    # Add new task to the event loop
    result = loop.run_until_complete(f())
    return result


def async_loop_wrapper_with_input(sagemaker_endpoint, type):
    global loop
    # check if there are any running or queued tasks inside the event loop
    if loop.is_running():
        # Calculate the number of running tasks
        while len([task for task in asyncio.all_tasks(loop) if not task.done()]) > MAX_RUNNING_LIMIT:
            logger.debug(f'Waiting for {MAX_RUNNING_LIMIT} running tasks to complete')
            time.sleep(1)
    else:
        # check if loop is closed and create a new one
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            # log this event since it should never happen
            logger.debug('Event loop was closed, created a new one')

    # Add new task to the event loop
    result = loop.run_until_complete(call_remote_inference(sagemaker_endpoint, type))
    return result


def call_interrogate_clip(sagemaker_endpoint, init_img, sketch, init_img_with_mask, inpaint_color_sketch,
                          init_img_inpaint, init_mask_inpaint):
    return async_loop_wrapper_with_input(sagemaker_endpoint, 'interrogate_clip')


def call_interrogate_deepbooru(sagemaker_endpoint, init_img, sketch, init_img_with_mask, inpaint_color_sketch,
                               init_img_inpaint, init_mask_inpaint):
    return async_loop_wrapper_with_input(sagemaker_endpoint, 'interrogate_deepbooru')


async def call_remote_inference(sagemaker_endpoint, type):
    logger.debug(f"chosen ep {sagemaker_endpoint}")
    logger.debug(f"inference type is {type}")

    if sagemaker_endpoint == '':
        image_list = []  # Return an empty list if selected_value is None
        info_text = ''
        infotexts = "Failed! Please choose the endpoint in 'InService' states "
        return image_list, info_text, plaintext_to_html(infotexts)
    elif sagemaker_endpoint == 'FAILURE':
        image_list = []  # Return an empty list if selected_value is None
        info_text = ''
        infotexts = "Failed upload the config to cloud  "
        return image_list, info_text, plaintext_to_html(infotexts)

    sagemaker_endpoint_status = sagemaker_endpoint.split("+")[1]

    if sagemaker_endpoint_status != "InService":
        image_list = []  # Return an empty list if selected_value is None
        info_text = ''
        infotexts = "Failed! Please choose the endpoint in 'InService' states "
        return image_list, info_text, plaintext_to_html(infotexts)

    api_gateway_url = get_variable_from_json('api_gateway_url')
    # Check if api_url ends with '/', if not append it
    if not api_gateway_url.endswith('/'):
        api_gateway_url += '/'
    api_key = get_variable_from_json('api_token')

    # stage 2: inference using endpoint_name
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    checkpoint_info['sagemaker_endpoint'] = sagemaker_endpoint.split("+")[0]
    payload = checkpoint_info
    payload['task_type'] = type
    logger.info(f"checkpointinfo is {payload}")

    inference_url = f"{api_gateway_url}inference/run-sagemaker-inference"
    response = requests.post(inference_url, json=payload, headers=headers)
    logger.info(f"Raw server response: {response.text}")
    try:
        r = response.json()
    except JSONDecodeError as e:
        logger.error(f"Failed to decode JSON response: {e}")
        logger.error(f"Raw server response: {response.text}")
    else:
        inference_id = r.get('inference_id')  # Assuming the response contains 'inference_id' field
        try:
            return process_result_by_inference_id(inference_id)
        except Exception as e:
            logger.error(f"Failed to get inference job {inference_id}, error: {e}")


def process_result_by_inference_id(inference_id):
    image_list = []  # Return an empty list if selected_value is None
    info_text = ''
    infotexts = f"Inference id is {inference_id}, please check all historical inference result in 'Inference Job' dropdown list"
    json_list = []
    prompt_txt = ''

    resp = get_inference_job(inference_id)
    if resp is None:
        logger.info(f"get_inference_job resp is null")
        return image_list, info_text, plaintext_to_html(infotexts), infotexts
    else:
        logger.debug(f"get_inference_job resp is {resp}")
        if resp['taskType'] in ['txt2img', 'img2img', 'interrogate_clip', 'interrogate_deepbooru']:
            while resp and resp['status'] == "inprogress":
                time.sleep(3)
                resp = get_inference_job(inference_id)
            if resp is None:
                logger.info(f"get_inference_job resp is null.")
                return image_list, info_text, plaintext_to_html(infotexts), infotexts
            if resp['status'] == "failed":
                infotexts = f"Inference job {inference_id} is failed, error message: {resp['sagemakerRaw']}"
                return image_list, info_text, plaintext_to_html(infotexts), infotexts
            elif resp['status'] == "succeed":
                if resp['taskType'] in ['interrogate_clip', 'interrogate_deepbooru']:
                    prompt_txt = resp['caption']
                    # return with default value, including image_list, info_text, infotexts
                    return image_list, info_text, plaintext_to_html(infotexts), prompt_txt
                images = get_inference_job_image_output(inference_id.strip())
                inference_param_json_list = get_inference_job_param_output(inference_id)
                # todo: these not need anymore
                if resp['taskType'] == "txt2img":
                    image_list = download_images(images, f"outputs/txt2img-images/{get_current_date()}/{inference_id}/")
                    json_list = download_images(inference_param_json_list,
                                                f"outputs/txt2img-images/{get_current_date()}/{inference_id}/")
                    json_file = f"outputs/txt2img-images/{get_current_date()}/{inference_id}/{inference_id}_param.json"
                elif resp['taskType'] == "img2img":
                    image_list = download_images(images, f"outputs/img2img-images/{get_current_date()}/{inference_id}/")
                    json_list = download_images(inference_param_json_list,
                                                f"outputs/img2img-images/{get_current_date()}/{inference_id}/")
                    json_file = f"outputs/img2img-images/{get_current_date()}/{inference_id}/{inference_id}_param.json"
                if os.path.isfile(json_file):
                    with open(json_file) as f:
                        log_file = json.load(f)
                        info_text = log_file["info"]
                        infotexts = f"Inference id is {inference_id}\n" + json.loads(info_text)["infotexts"][0]
                else:
                    logger.debug(f"File {json_file} does not exist.")
                    info_text = 'something wrong when trying to download the inference parameters'
                    infotexts = info_text
                return image_list, info_text, plaintext_to_html(infotexts), infotexts
            else:
                logger.debug(f"inference job status is {resp['status']}")
                return image_list, info_text, plaintext_to_html(infotexts), infotexts
        else:
            return image_list, info_text, plaintext_to_html(infotexts), infotexts



def modelmerger_on_cloud_func(primary_model_name, secondary_model_name, teritary_model_name):
    logger.debug(f"function under development, current checkpoint_info is {checkpoint_info}")
    api_gateway_url = get_variable_from_json('api_gateway_url')
    # Check if api_url ends with '/', if not append it
    if not api_gateway_url.endswith('/'):
        api_gateway_url += '/'
    api_key = get_variable_from_json('api_token')

    if api_gateway_url is None:
        logger.debug(f"modelmerger: failed to get the api-gateway url, can not fetch remote data")
        return []
    modelmerge_url = f"{api_gateway_url}inference/run-model-merge"

    payload = {
        "primary_model_name": primary_model_name,
        "secondary_model_name": secondary_model_name,
        "tertiary_model_name": teritary_model_name
    }

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }

    response = requests.post(modelmerge_url, json=payload, headers=headers)

    try:
        r = response.json()
    except JSONDecodeError as e:
        logger.error(f"Failed to decode JSON response: {e}")
        logger.error(f"Raw server response: {response.text}")
    else:
        logger.debug(f"response for rest api {r}")


# def txt2img_config_save():
#     # placeholder for saving txt2img config
#     pass

def displayEndpointInfo(input_string: str):
    logger.debug(f"selected value is {input_string}")
    if not input_string:
        return
    parts = input_string.split('+')

    if len(parts) < 2:
        return plaintext_to_html("")

    endpoint_job_id, status = parts[0], parts[1]

    if status == 'failed':
        response = server_request(f'inference/get-endpoint-deployment-job?jobID={endpoint_job_id}')
        # Do something with the response
        r = response.json()
        if "error" in r:
            return plaintext_to_html(r["error"])
        else:
            return plaintext_to_html(r["EndpointDeploymentJobId"])
    else:
        return plaintext_to_html("")


def update_txt2imgPrompt_from_TextualInversion(selected_items, txt2img_prompt):
    return update_txt2imgPrompt_from_model_select(selected_items, txt2img_prompt, 'embeddings', False)


def update_txt2imgPrompt_from_Hypernetworks(selected_items, txt2img_prompt):
    return update_txt2imgPrompt_from_model_select(selected_items, txt2img_prompt, 'hypernetworks', True)


def update_txt2imgPrompt_from_Lora(selected_items, txt2img_prompt):
    return update_txt2imgPrompt_from_model_select(selected_items, txt2img_prompt, 'Lora', True)


def update_txt2imgPrompt_from_model_select(selected_items, txt2img_prompt, model_name='embeddings',
                                           with_angle_brackets=False):
    logger.debug(selected_items)  # example ['FastNegativeV2.pt']
    logger.debug(txt2img_prompt)
    logger.debug(get_model_list_by_type('embeddings'))
    full_dropdown_items = get_model_list_by_type(model_name)  # example ['FastNegativeV2.pt', 'okuryl3nko.pt']

    # Remove extensions from selected_items and full_dropdown_items
    selected_items = [item.split('.')[0] for item in selected_items]
    full_dropdown_items = [item.split('.')[0] for item in full_dropdown_items]

    # Loop over each item in full_dropdown_items and remove it from txt2img_prompt
    type_str = ''
    if model_name == 'Lora':
        type_str = 'lora:'
    elif model_name == 'hypernetworks':
        type_str = 'hypernet:'
    for item in full_dropdown_items:
        if with_angle_brackets:
            txt2img_prompt = re.sub(f'<{type_str}{item}:\d+>', "", txt2img_prompt).strip()
        else:
            txt2img_prompt = txt2img_prompt.replace(item, "").strip()

    # Loop over each item in selected_items and append it to txt2img_prompt
    for item in selected_items:
        if with_angle_brackets:
            txt2img_prompt += ' ' + '<' + type_str + item + ':1>'
        else:
            txt2img_prompt += ' ' + item

    # Remove any leading or trailing whitespace
    txt2img_prompt = txt2img_prompt.strip()

    return txt2img_prompt


def fake_gan(selected_value, original_prompt):
    logger.debug(f"selected value is {selected_value}")
    logger.debug(f"original prompt is {original_prompt}")
    if selected_value is not None:
        delimiter = "-->"
        parts = selected_value.split(delimiter)
        # Extract the InferenceJobId value
        inference_job_id = parts[3].strip()
        inference_job_status = parts[2].strip()
        inference_job_taskType = parts[1].strip()
        if inference_job_status == 'inprogress':
            return [], [], plaintext_to_html('inference still in progress')

        if inference_job_taskType in ["txt2img", "img2img"]:
            prompt_txt = original_prompt
            images = get_inference_job_image_output(inference_job_id)
            image_list = []
            json_list = []
            inference_pram_json_list = get_inference_job_param_output(inference_job_id)
            # output directory mapping to task type
            if inference_job_taskType == "txt2img":
                image_list = download_images(images, f"outputs/txt2img-images/{get_current_date()}/{inference_job_id}/")
                json_list = download_images(inference_pram_json_list,
                                            f"outputs/txt2img-images/{get_current_date()}/{inference_job_id}/")
                json_file = f"outputs/txt2img-images/{get_current_date()}/{inference_job_id}/{inference_job_id}_param.json"
            elif inference_job_taskType == "img2img":
                image_list = download_images(images, f"outputs/img2img-images/{get_current_date()}/{inference_job_id}/")
                json_list = download_images(inference_pram_json_list,
                                            f"outputs/img2img-images/{get_current_date()}/{inference_job_id}/")
                json_file = f"outputs/img2img-images/{get_current_date()}/{inference_job_id}/{inference_job_id}_param.json"
            logger.debug(f"{str(images)}")
            logger.debug(f"{str(inference_pram_json_list)}")
            if os.path.isfile(json_file):
                with open(json_file) as f:
                    log_file = json.load(f)
                    info_text = log_file["info"]
                    infotexts = json.loads(info_text)["infotexts"][0]
            else:
                logger.debug(f"File {json_file} does not exist.")
                info_text = 'something wrong when trying to download the inference parameters'
                infotexts = 'something wrong when trying to download the inference parameters'
        elif inference_job_taskType in ["interrogate_clip", "interrogate_deepbooru"]:
            job_status = get_inference_job(inference_job_id)
            logger.debug(job_status)
            caption = job_status['caption']
            prompt_txt = caption
            image_list = []  # Return an empty list if selected_value is None
            json_list = []
            info_text = ''
            infotexts = ''
    else:
        prompt_txt = original_prompt
        image_list = []  # Return an empty list if selected_value is None
        json_list = []
        info_text = ''
        infotexts = ''
    return image_list, info_text, plaintext_to_html(infotexts), prompt_txt


def display_inference_result(inference_id: str):
    logger.debug(f"selected value is {inference_id}")
    if inference_id is not None:
        # Extract the InferenceJobId value
        inference_job_id = inference_id
        images = get_inference_job_image_output(inference_job_id)
        image_list = []
        image_list = download_images(images, f"outputs/txt2img-images/{get_current_date()}/{inference_job_id}/")

        inference_pram_json_list = get_inference_job_param_output(inference_job_id)
        json_list = []
        json_list = download_images(inference_pram_json_list,
                                    f"outputs/txt2img-images/{get_current_date()}/{inference_job_id}/")

        logger.debug(f"{str(images)}")
        logger.debug(f"{str(inference_pram_json_list)}")

        json_file = f"outputs/txt2img-images/{get_current_date()}/{inference_job_id}/{inference_job_id}_param.json"

        f = open(json_file)

        log_file = json.load(f)

        info_text = log_file["info"]

        infotexts = json.loads(info_text)["infotexts"][0]
    else:
        image_list = []  # Return an empty list if selected_value is None
        json_list = []
        info_text = ''

    return image_list, info_text, plaintext_to_html(infotexts)


def init_refresh_resource_list_from_cloud(username):
    logger.debug(f"start refreshing resource list from cloud")
    if get_variable_from_json('api_gateway_url') is not None:
        if not cloud_auth_manager.enableAuth:
            # api_manager.list_all_sagemaker_endpoints()
            refresh_all_models(username)
            # get_texual_inversion_list()
            # get_lora_list()
            # get_hypernetwork_list()
            # get_controlnet_model_list()
            # get_inference_job_list()
        else:
            logger.debug('auth enabled, not preload load any model')
    else:
        logger.debug(f"there is no api-gateway url and token in local file,")


def on_txt_time_change(start_time, end_time):
    logger.debug(f"!!!!!!!!!on_txt_time_change!!!!!!{start_time},{end_time}")
    global start_time_picker_txt_value
    global end_time_picker_txt_value
    start_time_picker_txt_value = start_time
    end_time_picker_txt_value = end_time
    return query_inference_job_list(txt_task_type, txt_status, txt_endpoint, txt_checkpoint, "txt2img")


def on_img_time_change(start_time, end_time):
    logger.debug(f"!!!!!!!!!on_img_time_change!!!!!!{start_time},{end_time}")
    global start_time_picker_img_value
    global end_time_picker_img_value
    start_time_picker_img_value = start_time
    end_time_picker_img_value = end_time
    return query_inference_job_list(img_task_type, img_status, img_endpoint, img_checkpoint, "img2img")


def load_inference_job_list(username, usertoken):
    inference_jobs = [None_Option_For_On_Cloud_Model]
    inferences_jobs_list = api_manager.list_all_inference_jobs_on_cloud(username, usertoken)

    temp_list = []
    for obj in inferences_jobs_list:
        if obj.get('completeTime') is None:
            complete_time = obj.get('startTime')
        else:
            complete_time = obj.get('completeTime')
        status = obj.get('status')
        task_type = obj.get('taskType', 'txt2img')
        inference_job_id = obj.get('InferenceJobId')
        # if filter_checkbox and task_type not in selected_types:
        #     continue
        temp_list.append((complete_time, f"{complete_time}-->{task_type}-->{status}-->{inference_job_id}"))
    # Sort the list based on completeTime in ascending order
    sorted_list = sorted(temp_list, key=lambda x: x[0], reverse=False)
    # Append the sorted combined strings to the txt2img_inference_job_ids list
    for item in sorted_list:
        inference_jobs.append(item[1])

    return inference_jobs


def load_model_list(username, user_token):
    models_on_cloud = [None_Option_For_On_Cloud_Model]
    models_on_cloud += list(set([model['name'] for model in api_manager.list_models_on_cloud(username, user_token)]))
    return models_on_cloud


def load_lora_models(username, user_token):
    return list(set([model['name'] for model in api_manager.list_models_on_cloud(username, user_token, types='Lora')]))


def load_hypernetworks_models(username, user_token):
    return list(set([model['name'] for model in api_manager.list_models_on_cloud(username, user_token, types='hypernetworks')]))


def load_vae_list(username, user_token):
    vae_model_on_cloud = ['Automatic', 'None']
    vae_model_on_cloud += list(set([model['name'] for model in api_manager.list_models_on_cloud(username, user_token, types='VAE')]))

    return vae_model_on_cloud


def load_controlnet_list(username, user_token):
    vae_model_on_cloud = ['None']
    vae_model_on_cloud += list(set([model['name'] for model in api_manager.list_models_on_cloud(username, user_token, types='ControlNet')]))
    return vae_model_on_cloud


def load_embeddings_list(username, user_token):
    # vae_model_on_cloud = ['None']
    vae_model_on_cloud = list(set([model['name'] for model in api_manager.list_models_on_cloud(username, user_token, types='embeddings')]))
    return vae_model_on_cloud


def create_ui(is_img2img):
    global txt2img_gallery, txt2img_generation_info
    import modules.ui

    # init_refresh_resource_list_from_cloud()

    with gr.Blocks() as sagemaker_inference_tab:
        gr.HTML('<h3>Amazon SageMaker Inference</h3>')
        sagemaker_html_log = gr.HTML(elem_id=f'html_log_sagemaker')
        with gr.Column():
            with gr.Row():
                lora_and_hypernet_models_state = gr.State({})
                sd_model_on_cloud_dropdown = gr.Dropdown(choices=[], value=None_Option_For_On_Cloud_Model,
                                                         label='Stable Diffusion Checkpoint Used on Cloud')

                create_refresh_button_by_user(sd_model_on_cloud_dropdown,
                                              lambda *args: None,
                                              lambda username: {
                                                  'choices': load_model_list(username, username)
                                              }, 'refresh_cloud_model_down')

            with gr.Row():
                sd_vae_on_cloud_dropdown = gr.Dropdown(choices=[], value='Automatic',
                                                       label='SD Vae on Cloud')

                create_refresh_button_by_user(sd_vae_on_cloud_dropdown,
                                              lambda *args: None,
                                              lambda username: {
                                                  'choices': load_vae_list(username, username)
                                              }, 'refresh_cloud_vae_down')
            with gr.Row(visible=is_img2img):
                gr.HTML('<br/>')

            with gr.Row(visible=is_img2img):
                global generate_on_cloud_button_with_js
                # if not is_img2img:
                #     generate_on_cloud_button_with_js = gr.Button(value="Generate on Cloud", variant='primary', elem_id="generate_on_cloud_with_cloud_config_button",queue=True, show_progress=True)
                global generate_on_cloud_button_with_js_img2img
                global interrogate_clip_on_cloud_button
                global interrogate_deep_booru_on_cloud_button

                interrogate_clip_on_cloud_button = gr.Button(value="Interrogate CLIP",  variant='primary',
                                                             elem_id="interrogate_clip_on_cloud_button", visible=False)
                interrogate_deep_booru_on_cloud_button = gr.Button(value="Interrogte DeepBooru",  variant='primary',
                                                                   elem_id="interrogate_deep_booru_on_cloud_button", visible=False)
            with gr.Row():
                gr.HTML('<br/>')

            with gr.Row():
                global inference_job_dropdown
                # global txt2img_inference_job_ids

                inference_job_dropdown = gr.Dropdown(choices=[], value=None_Option_For_On_Cloud_Model,
                                                     label="Inference Job: Time-Type-Status-Uuid")
                create_refresh_button_by_user(inference_job_dropdown,
                                              lambda *args: None,
                                              lambda username: {
                                                  'choices': load_inference_job_list(username, username)
                                              }, 'refresh_inference_job_down')
                # inference_job_dropdown = gr.Dropdown(choices=txt2img_inference_job_ids,
                #                                      label="Inference Job: Time-Type-Status-Uuid",
                #                                      elem_id="txt2img_inference_job_ids_dropdown"
                #                                      )
                # txt2img_inference_job_ids_refresh_button = create_refresh_button(inference_job_dropdown,
                #                                                                  query_inference_job_list,
                #                                                                  lambda: {
                #                                                                     "choices": txt2img_inference_job_ids,
                #                                                                     "value": None},
                #                                                                  "refresh_txt2img_inference_job_ids")
            # fixme: inference filters need to be fixed
            # with gr.Row():
            #     inference_job_filter = gr.Checkbox(
            #         label="Advanced Inference Job filter", value=False, visible=True
            #     )
            #     inference_job_page = gr.Checkbox(label="Show All(unchecked: max 10 items)",
            #                                      elem_id="inference_job_page_checkbox", value=False)
            # with gr.Row(variant='panel', visible=False) as filter_row:
            #     with gr.Column(scale=1):
            #         gr.HTML(value="Inference Job type filters")
            #     with gr.Column(scale=2):
            #         with gr.Row():
            #             task_type_choices = ["txt2img", "img2img", "interrogate_clip", "interrogate_deepbooru"]
            #             task_type_dropdown = gr.Dropdown(label="Task Type", choices=task_type_choices,
            #                                              elem_id="task_type_ids_dropdown")
            #             status_choices = ["succeed", "inprogress", "failed"]
            #             status_dropdown = gr.Dropdown(label="Status", choices=status_choices,
            #                                           elem_id="task_status_dropdown")
            #         # with gr.Row():
            #         #     sagemaker_endpoint_filter = gr.Dropdown(api_manager.list_all_sagemaker_endpoints(),
            #         #                                             label="SageMaker Endpoint",
            #         #                                             elem_id="sagemaker_endpoint_dropdown")
            #         #     modules.ui.create_refresh_button(sagemaker_endpoint_filter, lambda: None,
            #         #                                      lambda: {"choices": api_manager.list_all_sagemaker_endpoints()},
            #         #                                      "refresh_sagemaker_endpoints")
            #
            #         with gr.Row():
            #             sd_checkpoint_filter = gr.Dropdown(label="Checkpoint", choices=sorted(update_sd_checkpoints()),
            #                                                elem_id="stable_diffusion_checkpoint_dropdown")
            #             modules.ui.create_refresh_button(sd_checkpoint_filter, update_sd_checkpoints,
            #                                              lambda: {"choices": sorted(update_sd_checkpoints())},
            #                                              "refresh_sd_checkpoints")
            #         if is_img2img:
            #             with gr.Row():
            #                 start_time_picker_img = gr.HTML(elem_id="start_timepicker_img_e",
            #                                                 value="""
            #                                                 <span class="svelte-1ed2p3z" style="color: #6B7280">
            #                                                     Start Time
            #                                                     <input type="date"
            #                                                            lang="en"
            #                                                            id="start_timepicker_img"
            #                                                            min="2023-01-01"
            #                                                            max="2033-12-31"
            #                                                            class="wrap svelte-aqlk7e"
            #                                                            style="color: #6B7280"
            #                                                            onchange="inference_job_timepicker_img_change()" />
            #                                                 </span>
            #                                                 """)
            #                 end_time_picker_img = gr.HTML(elem_id="end_timepicker_img_e",
            #                                               value="""
            #                                               <span class="svelte-1ed2p3z" style="color: #6B7280">
            #                                                 End Time
            #                                                 <input type="date"
            #                                                        lang="en"
            #                                                        id="end_timepicker_img"
            #                                                        min="2023-01-01" max="2033-12-31"
            #                                                        class="wrap svelte-aqlk7e"
            #                                                        style="color: #6B7280"
            #                                                        onchange="inference_job_timepicker_img_change()">
            #                                               </span>
            #                                               """)
            #                 start_time_picker_img_hidden = gr.Button(elem_id="start_time_picker_img_hidden",
            #                                                          visible=True)
            #                 end_time_picker_img_hidden = gr.Button(elem_id="end_time_picker_img_hidden",
            #                                                        visible=True)
            #             start_time_picker_img_hidden.click(fn=on_img_time_change,
            #                                                _js='get_time_img_value',
            #                                                inputs=[start_time_picker_img, end_time_picker_img],
            #                                                outputs=inference_job_dropdown)
            #             end_time_picker_img_hidden.click(fn=on_img_time_change,
            #                                              _js='get_time_img_value',
            #                                              inputs=[start_time_picker_img, end_time_picker_img],
            #                                              outputs=inference_job_dropdown
            #                                              )
            #             task_type_dropdown.change(fn=query_img_inference_job_list,
            #                                       inputs=[task_type_dropdown, status_dropdown,
            #                                               sagemaker_endpoint_filter,
            #                                               sd_checkpoint_filter], outputs=inference_job_dropdown)
            #             status_dropdown.change(fn=query_img_inference_job_list,
            #                                    inputs=[task_type_dropdown, status_dropdown, sagemaker_endpoint_filter,
            #                                            sd_checkpoint_filter], outputs=inference_job_dropdown)
            #
            #             sagemaker_endpoint_filter.change(fn=query_img_inference_job_list,
            #                                              inputs=[task_type_dropdown, status_dropdown,
            #                                                      sagemaker_endpoint_filter,
            #                                                      sd_checkpoint_filter], outputs=inference_job_dropdown)
            #
            #             sd_checkpoint_filter.change(fn=query_img_inference_job_list,
            #                                         inputs=[task_type_dropdown, status_dropdown,
            #                                                 sagemaker_endpoint_filter,
            #                                                 sd_checkpoint_filter], outputs=inference_job_dropdown)
            #         else:
            #             with gr.Row():
            #                 start_time_picker_text = gr.HTML(elem_id="start_timepicker_text_e",
            #                                                  value="""
            #                                                  <span class="svelte-1ed2p3z" style="color: #6B7280">
            #                                                     Start Time
            #                                                     <input type="date" lang="en" id="start_timepicker_text"
            #                                                            min="2023-01-01" max="2033-12-31"
            #                                                            class="wrap svelte-aqlk7e" style="color: #6B7280"
            #                                                            onchange="inference_job_timepicker_text_change()">
            #                                                 </span>
            #                                                  """)
            #                 end_time_picker_text = gr.HTML(elem_id="end_timepicker_text_e",
            #                                                value="""
            #                                                <span class="svelte-1ed2p3z" style="color: #6B7280">
            #                                                     End Time
            #                                                     <input type="date" lang="en" id="end_timepicker_text"
            #                                                             min="2023-01-01" max="2033-12-31"
            #                                                             class="wrap svelte-aqlk7e"
            #                                                             style="color: #6B7280"
            #                                                             onchange="inference_job_timepicker_text_change()">
            #                                                </span>
            #                                                """)
            #                 start_time_picker_button_hidden = gr.Button(elem_id="start_time_picker_button_hidden",
            #                                                             visible=False)
            #                 end_time_picker_button_hidden = gr.Button(elem_id="end_time_picker_button_hidden",
            #                                                           visible=False)
            #             start_time_picker_button_hidden.click(fn=on_txt_time_change,
            #                                                   _js='get_time_button_value',
            #                                                   inputs=[start_time_picker_text, end_time_picker_text],
            #                                                   outputs=inference_job_dropdown)
            #             end_time_picker_button_hidden.click(fn=on_txt_time_change,
            #                                                 _js='get_time_button_value',
            #                                                 inputs=[start_time_picker_text, end_time_picker_text],
            #                                                 outputs=inference_job_dropdown)
            #             task_type_dropdown.change(fn=query_txt_inference_job_list,
            #                                       inputs=[task_type_dropdown, status_dropdown,
            #                                               sagemaker_endpoint_filter, sd_checkpoint_filter],
            #                                       outputs=inference_job_dropdown)
            #             status_dropdown.change(fn=query_txt_inference_job_list,
            #                                    inputs=[task_type_dropdown, status_dropdown,
            #                                            sagemaker_endpoint_filter,
            #                                            sd_checkpoint_filter], outputs=inference_job_dropdown)
            #             sagemaker_endpoint_filter.change(fn=query_txt_inference_job_list,
            #                                              inputs=[task_type_dropdown, status_dropdown,
            #                                                      sagemaker_endpoint_filter,
            #                                                      sd_checkpoint_filter], outputs=inference_job_dropdown)
            #             sd_checkpoint_filter.change(fn=query_txt_inference_job_list,
            #                                         inputs=[task_type_dropdown, status_dropdown,
            #                                                 sagemaker_endpoint_filter, sd_checkpoint_filter],
            #                                         outputs=inference_job_dropdown)
            #
            #         def toggle_new_rows(create_from):
            #             global start_time_picker_txt_value
            #             start_time_picker_txt_value = None
            #             global end_time_picker_txt_value
            #             end_time_picker_txt_value = None
            #             return [gr.update(visible=create_from), None, None, None, None]
            #
            #         inference_job_filter.change(
            #             fn=toggle_new_rows,
            #             inputs=[inference_job_filter],
            #             outputs=[filter_row, task_type_dropdown, status_dropdown, sagemaker_endpoint_filter,
            #                      sd_checkpoint_filter],
            #         )
            #         hidden_check_type = gr.Textbox(elem_id="hidden_check_type", value=is_img2img, visible=False)
            #         inference_job_page.change(fn=query_page_inference_job_list,
            #                                   inputs=[task_type_dropdown, status_dropdown,
            #                                           sagemaker_endpoint_filter,
            #                                           sd_checkpoint_filter, hidden_check_type,
            #                                           inference_job_page],
            #
            #                                   outputs=inference_job_dropdown)

                def setup_inference_for_plugin(pr: gr.Request):
                    models_on_cloud = load_model_list(pr.username, pr.username)
                    vae_model_on_cloud = load_vae_list(pr.username, pr.username)
                    inference_jobs = load_inference_job_list(pr.username, pr.username)
                    lora_models_on_cloud = load_lora_models(username=pr.username, user_token=pr.username)
                    hypernetworks_models_on_cloud = load_hypernetworks_models(pr.username, pr.username)
                    controlnet_list = load_controlnet_list(pr.username, pr.username)
                    lora_hypernets = {
                        'lora': lora_models_on_cloud,
                        'hypernet': hypernetworks_models_on_cloud,
                        'controlnet': controlnet_list,
                    }

                    return lora_hypernets, \
                        gr.update(choices=models_on_cloud), \
                        gr.update(choices=inference_jobs), \
                        gr.update(choices=vae_model_on_cloud)

                sagemaker_inference_tab.load(fn=setup_inference_for_plugin, inputs=[],
                                             outputs=[
                                                 lora_and_hypernet_models_state,
                                                 sd_model_on_cloud_dropdown,
                                                 inference_job_dropdown,
                                                 sd_vae_on_cloud_dropdown]
                                             )
    with gr.Group():
        with gr.Accordion("Open for Checkpoint Merge in the Cloud!", visible=False, open=False):
            sagemaker_html_log = gr.HTML(elem_id=f'html_log_sagemaker')
            with FormRow(elem_id="modelmerger_models_in_the_cloud"):
                global primary_model_name
                primary_model_name = gr.Dropdown(elem_id="modelmerger_primary_model_name_in_the_cloud",
                                                 label="Primary model (A) in the cloud")
                create_refresh_button_by_user(primary_model_name, lambda *args: None,
                                      lambda username: {"choices": sorted(update_sd_checkpoints(username))},
                                      "refresh_checkpoint_A_in_the_cloud")

                global secondary_model_name
                secondary_model_name = gr.Dropdown(elem_id="modelmerger_secondary_model_name_in_the_cloud",
                                                   label="Secondary model (B) in the cloud")
                create_refresh_button_by_user(secondary_model_name, lambda *args: None,
                                      lambda username: {"choices": sorted(update_sd_checkpoints(username))},
                                      "refresh_checkpoint_B_in_the_cloud")

                global tertiary_model_name
                tertiary_model_name = gr.Dropdown(elem_id="modelmerger_tertiary_model_name_in_the_cloud",
                                                  label="Tertiary model (C) in the cloud")
                create_refresh_button_by_user(tertiary_model_name, lambda *args: None,
                                      lambda username: {"choices": sorted(update_sd_checkpoints(username))},
                                      "refresh_checkpoint_C_in_the_cloud")
            with gr.Row():
                global modelmerger_merge_on_cloud
                modelmerger_merge_on_cloud = gr.Button(elem_id="modelmerger_merge_in_the_cloud", value="Merge on Cloud",
                                                       variant='primary')

    return sd_model_on_cloud_dropdown, sd_vae_on_cloud_dropdown, inference_job_dropdown, primary_model_name, secondary_model_name, tertiary_model_name, modelmerger_merge_on_cloud, lora_and_hypernet_models_state
