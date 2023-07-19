import copy
import itertools
import os
from pathlib import Path
import html
import boto3
import time

import json
import requests
import base64
from urllib.parse import urljoin

import gradio as gr

from modules import shared, scripts
from modules.ui import create_refresh_button
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

inference_job_dropdown = None
textual_inversion_dropdown = None
hyperNetwork_dropdown = None
lora_dropdown = None
sagemaker_endpoint = None

primary_model_name = None
secondary_model_name = None
tertiary_model_name = None

#TODO: convert to dynamically init the following variables
sagemaker_endpoints = []
txt2img_inference_job_ids = []

sd_checkpoints = []
textual_inversion_list = []
lora_list = []
hyperNetwork_list = []
ControlNet_model_list = []

# Initial checkpoints information
checkpoint_info = {}
checkpoint_type = ["Stable-diffusion", "embeddings", "Lora", "hypernetworks", "ControlNet"]
checkpoint_name = ["stable_diffusion", "embeddings", "lora", "hypernetworks", "controlnet"]
stable_diffusion_list = []
embeddings_list = []
lora_list = []
hypernetworks_list = []
controlnet_list = []
for ckpt_type, ckpt_name in zip(checkpoint_type, checkpoint_name):
    checkpoint_info[ckpt_type] = {}
# get api_gateway_url
api_gateway_url = get_variable_from_json('api_gateway_url')
api_key = get_variable_from_json('api_token')


def plaintext_to_html(text):
    text = "<p>" + "<br>\n".join([f"{html.escape(x)}" for x in text.split('\n')]) + "</p>"
    return text

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
    response = requests.post(list_endpoint_url, data=params, headers=headers)
    return response


def datetime_to_short_form(datetime_str):
    dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S.%f")
    short_form = dt.strftime("%Y-%m-%d-%H-%M-%S")
    return short_form

def update_sagemaker_endpoints():
    global sagemaker_endpoints

    sagemaker_endpoints.clear()
    try:
        response = server_request('inference/list-endpoint-deployment-jobs')
        r = response.json()
        if r:
            sagemaker_endpoints.clear()  # Clear the existing list before appending new values
            sagemaker_raw_endpoints = []
            for obj in r:
                if "EndpointDeploymentJobId" in obj :
                    if "endpoint_name" in obj:
                        endpoint_name = obj["endpoint_name"]
                        endpoint_status = obj["endpoint_status"]
                    else:
                        endpoint_name = obj["EndpointDeploymentJobId"]
                        endpoint_status = obj["status"]

                    # Skip if status is 'deleted'
                    if endpoint_status == 'deleted':
                        continue

                    if "endTime" in obj:
                        endpoint_time = obj["endTime"]
                    else:
                        endpoint_time = "N/A"

                    endpoint_info = f"{endpoint_name}+{endpoint_status}+{endpoint_time}"
                    sagemaker_raw_endpoints.append(endpoint_info)

            # Sort the list based on completeTime in descending order
            sagemaker_endpoints= sorted(sagemaker_raw_endpoints, key=lambda x: x.split('+')[-1], reverse=True)

        else:
            print("The API response is empty for update_sagemaker_endpoints().")

    except Exception as e:
        print(f"An error occurred while updating SageMaker endpoints: {e}")


def update_txt2img_inference_job_ids(inference_job_dropdown, txt2img_type_checkbox=True, img2img_type_checkbox=True, interrogate_type_checkbox=True):
    # global txt2img_inference_job_ids
    return get_inference_job_list(txt2img_type_checkbox, img2img_type_checkbox, interrogate_type_checkbox)

def origin_update_txt2img_inference_job_ids():
    # global origin_txt2img_inference_job_ids
    return get_inference_job_list(True, True, True)


def get_inference_job_list(txt2img_type_checkbox=True, img2img_type_checkbox=True, interrogate_type_checkbox=True):
    global txt2img_inference_job_ids
    try:
        txt2img_inference_job_ids.clear()  # Clear the existing list before appending new values
        response = server_request('inference/list-inference-jobs')
        r = response.json()
        # print(f"response: {response.json()}")
        filter_checkbox = False
        selected_types = []
        if txt2img_type_checkbox:
            selected_types.append('txt2img')
            filter_checkbox = True
        if img2img_type_checkbox:
            selected_types.append('img2img')
            filter_checkbox = True
        if interrogate_type_checkbox:
            selected_types.append('interrogate_deepbooru')
            filter_checkbox = True
        print(f"selected_types: {selected_types}")
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
                if filter_checkbox and task_type not in selected_types:
                    continue
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
            print("The API response is empty.")
            return gr.Dropdown.update(choices=[])

    except Exception as e:
        print("Exception occurred when fetching inference_job_ids")
        return gr.Dropdown.update(choices=[])


def query_inference_job_list(status: str, task_type: str, start_time: str, end_time: str, endpoint: str, checkpoint: list):
    print(
        f"query_inference_job_list start！！{status},{task_type},{start_time},{end_time},{endpoint},{checkpoint}")
    try:
        body_params = {}
        if status:
            body_params['status'] = status
        if task_type:
            body_params['task_type'] = task_type
        if start_time:
            body_params['start_time'] = start_time
        if end_time:
            body_params['end_time'] = end_time
        if endpoint:
            body_params['endpoint'] = endpoint
        if checkpoint:
            body_params['checkpoint'] = checkpoint
        response = server_request_post(f'inference/query-inference-jobs', body_params)
        r = response.json()
        print(r)
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
            print("The API response is empty.")
            return gr.Dropdown.update(choices=[])
    except Exception as e:
        print("Exception occurred when fetching inference_job_ids")
        return gr.Dropdown.update(choices=[])


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
        print(f"An error occurred while getting inference job image output: {e}")
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
        print(f"An error occurred while getting inference job param output: {e}")
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
            print(f"Error downloading image {url}: {e}")
    return image_list


def get_model_list_by_type(model_type):

    api_gateway_url = get_variable_from_json('api_gateway_url')
    api_key = get_variable_from_json('api_token')

    # check if api_gateway_url and api_key are set
    if api_gateway_url is None or api_key is None:
        print("api_gateway_url or api_key is not set")
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
        response = requests.get(url=url, headers={'x-api-key': api_key})
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
            ckpt_type = ckpt["type"]
            for ckpt_name in ckpt["name"]:
                ckpt_s3_pos = f"{ckpt['s3Location']}/{ckpt_name}"
                checkpoint_info[ckpt_type][ckpt_name] = ckpt_s3_pos
                checkpoint_list.append(ckpt_name)

        return checkpoint_list
    except Exception as e:
        print(f"Error fetching model list: {e}")
        return []


def update_sd_checkpoints():
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

def refresh_all_models():
    api_gateway_url = get_variable_from_json('api_gateway_url')
    api_key = get_variable_from_json('api_token')
    try:
        for rp, name in zip(checkpoint_type, checkpoint_name):
            url = api_gateway_url + f"checkpoints?status=Active&types={rp}"
            response = requests.get(url=url, headers={'x-api-key': api_key})
            json_response = response.json()
            # print(f"response url json for model {rp} is {json_response}")
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
        print(f"Error refresh all models: {e}")

def sagemaker_upload_model_s3(sd_checkpoints_path, textual_inversion_path, lora_path, hypernetwork_path, controlnet_model_path):
    log = "start upload model to s3..."

    local_paths = [sd_checkpoints_path, textual_inversion_path, lora_path, hypernetwork_path, controlnet_model_path]

    print(f"Refresh checkpionts before upload to get rid of duplicate uploads...")
    refresh_all_models()

    for lp, rp in zip(local_paths, checkpoint_type):
        if lp == "" or not lp:
            continue
        print(f"lp is {lp}")
        model_name = lp.split(os.sep)[-1]

        exist_model_list = list(checkpoint_info[rp].keys())

        if model_name in exist_model_list:
            print(f"!!!skip to upload duplicate model {model_name}")
            continue

        part_size = 1000 * 1024 * 1024
        file_size = os.stat(lp)
        parts_number = math.ceil(file_size.st_size/part_size)
        print('!!!!!!!!!!', file_size, parts_number)

        #local_tar_path = f'{model_name}.tar'
        local_tar_path = model_name
        payload = {
            "checkpoint_type": rp,
            "filenames": [{
                "filename": local_tar_path,
                "parts_number": parts_number
            }],
            "params": {"message": "placeholder for chkpts upload test"}
        }
        api_gateway_url = get_variable_from_json('api_gateway_url')
        # Check if api_url ends with '/', if not append it
        if not api_gateway_url.endswith('/'):
            api_gateway_url += '/'
        api_key = get_variable_from_json('api_token')
        print('!!!!!!api_gateway_url', api_gateway_url)

        url = str(api_gateway_url) + "checkpoint"

        print(f"Post request for upload s3 presign url: {url}")

        response = requests.post(url=url, json=payload, headers={'x-api-key': api_key})

        try:
            json_response = response.json()
            # print(f"Response json {json_response}")
            s3_base = json_response["checkpoint"]["s3_location"]
            checkpoint_id = json_response["checkpoint"]["id"]
            print(f"Upload to S3 {s3_base}")
            print(f"Checkpoint ID: {checkpoint_id}")

            #s3_presigned_url = json_response["s3PresignUrl"][model_name]
            s3_signed_urls_resp = json_response["s3PresignUrl"][local_tar_path]
            # Upload src model to S3.
            if rp != "embeddings" :
                local_model_path_in_repo = os.sep.join(['models', rp, model_name])
            else:
                local_model_path_in_repo = os.sep.join([rp, model_name])
            #local_tar_path = f'{model_name}.tar'
            print("Pack the model file.")
            # os.system(f"cp -f {lp} {local_model_path_in_repo}")
            cp(lp, local_model_path_in_repo, recursive=True)
            if rp == "Stable-diffusion":
                model_yaml_name = model_name.split('.')[0] + ".yaml"
                local_model_yaml_path = os.sep.join([*lp.split(os.sep)[:-1], model_yaml_name])
                local_model_yaml_path_in_repo = os.sep.join(["models", rp, model_yaml_name])
                if os.path.isfile(local_model_yaml_path):
                    # os.system(f"cp -f {local_model_yaml_path} {local_model_yaml_path_in_repo}")
                    # os.system(f"tar cvf {local_tar_path} {local_model_path_in_repo} {local_model_yaml_path_in_repo}")
                    cp(local_model_yaml_path, local_model_yaml_path_in_repo, recursive=True)
                    tar(mode='c', archive=local_tar_path, sfiles=[local_model_path_in_repo, local_model_yaml_path_in_repo], verbose=True)
                else:
                    # os.system(f"tar cvf {local_tar_path} {local_model_path_in_repo}")
                    tar(mode='c', archive=local_tar_path, sfiles=[local_model_path_in_repo], verbose=True)
            else:
                # os.system(f"tar cvf {local_tar_path} {local_model_path_in_repo}")
                tar(mode='c', archive=local_tar_path, sfiles=[local_model_path_in_repo], verbose=True)
            #upload_file_to_s3_by_presign_url(local_tar_path, s3_presigned_url)
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
            print(response)

            log = f"\n finish upload {local_tar_path} to {s3_base}"

            # os.system(f"rm {local_tar_path}")
            rm(local_tar_path, recursive=True)
        except Exception as e:
            print(f"fail to upload model {lp}, error: {e}")

    print(f"Refresh checkpionts after upload...")
    refresh_all_models()

    return plaintext_to_html(log), None, None, None, None, None

def generate_on_cloud(sagemaker_endpoint):
    print(f"checkpiont_info {checkpoint_info}")
    print(f"sagemaker endpoint {sagemaker_endpoint}")
    text = "failed to check endpoint"
    return plaintext_to_html(text)

# create a global event loop and apply the patch to allow nested event loops in single thread
loop = asyncio.get_event_loop()
nest_asyncio.apply()

MAX_RUNNING_LIMIT = 10

def async_loop_wrapper_with_input(sagemaker_endpoint, type):
    global loop
    # check if there are any running or queued tasks inside the event loop
    if loop.is_running():
        # Calculate the number of running tasks
        while len([task for task in asyncio.all_tasks(loop) if not task.done()]) > MAX_RUNNING_LIMIT:
            print(f'Waiting for {MAX_RUNNING_LIMIT} running tasks to complete')
            time.sleep(1)
    else:
        # check if loop is closed and create a new one
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            # log this event since it should never happen
            print('Event loop was closed, created a new one')

    # Add new task to the event loop
    result = loop.run_until_complete(call_remote_inference(sagemaker_endpoint, type))
    return result

def call_txt2img_inference(sagemaker_endpoint):
    return async_loop_wrapper_with_input(sagemaker_endpoint, 'txt2img')

def call_img2img_inference(sagemaker_endpoint, init_img, sketch, init_img_with_mask, inpaint_color_sketch, init_img_inpaint, init_mask_inpaint):
    return async_loop_wrapper_with_input(sagemaker_endpoint, 'img2img')

def call_interrogate_clip(sagemaker_endpoint, init_img, sketch, init_img_with_mask, inpaint_color_sketch, init_img_inpaint, init_mask_inpaint):
    return async_loop_wrapper_with_input(sagemaker_endpoint, 'interrogate_clip')

def call_interrogate_deepbooru(sagemaker_endpoint, init_img, sketch, init_img_with_mask, inpaint_color_sketch, init_img_inpaint, init_mask_inpaint):
    return async_loop_wrapper_with_input(sagemaker_endpoint, 'interrogate_deepbooru')

async def call_remote_inference(sagemaker_endpoint, type):
    print(f"chosen ep {sagemaker_endpoint}")
    print(f"inference type is {type}")

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
    print(f"checkpointinfo is {payload}")

    inference_url = f"{api_gateway_url}inference/run-sagemaker-inference"
    response = requests.post(inference_url, json=payload, headers=headers)
    print(f"Raw server response: {response.text}")
    try:
        r = response.json()
    except JSONDecodeError as e:
        print(f"Failed to decode JSON response: {e}")
        print(f"Raw server response: {response.text}")
    else:
        inference_id = r.get('inference_id')  # Assuming the response contains 'inference_id' field
        image_list = []  # Return an empty list if selected_value is None
        info_text = ''
        infotexts = f"Inference id is {inference_id}, please check all historical inference result in 'Inference Job' dropdown list"
        json_list = []
        prompt_txt = ''

        try:
            resp = get_inference_job(inference_id)
            if resp is None:
                return image_list, info_text, plaintext_to_html(infotexts)
            else:
                if resp['taskType'] in ['txt2img', 'img2img', 'interrogate_clip', 'interrogate_deepbooru']:
                    while resp['status'] == "inprogress":
                        time.sleep(3)
                        resp = get_inference_job(inference_id)
                    if resp['status'] == "failed":
                        infotexts = f"Inference job {inference_id} is failed"
                        return image_list, info_text, plaintext_to_html(infotexts)
                    elif resp['status'] == "succeed":
                        if resp['taskType'] in ['interrogate_clip', 'interrogate_deepbooru']:
                            prompt_txt = resp['caption']
                            # return with default value, including image_list, info_text, infotexts
                            return image_list, info_text, plaintext_to_html(infotexts), prompt_txt
                        images = get_inference_job_image_output(inference_id.strip())
                        inference_param_json_list = get_inference_job_param_output(inference_id)
                        if resp['taskType'] == "txt2img":
                            image_list = download_images(images,f"outputs/txt2img-images/{get_current_date()}/{inference_id}/")
                            json_list = download_images(inference_param_json_list, f"outputs/txt2img-images/{get_current_date()}/{inference_id}/")
                            json_file = f"outputs/txt2img-images/{get_current_date()}/{inference_id}/{inference_id}_param.json"
                        elif resp['taskType'] == "img2img":
                            image_list = download_images(images,f"outputs/img2img-images/{get_current_date()}/{inference_id}/")
                            json_list = download_images(inference_param_json_list, f"outputs/img2img-images/{get_current_date()}/{inference_id}/")
                            json_file = f"outputs/img2img-images/{get_current_date()}/{inference_id}/{inference_id}_param.json"
                        if os.path.isfile(json_file):
                            with open(json_file) as f:
                                log_file = json.load(f)
                                info_text = log_file["info"]
                                infotexts = f"Inference id is {inference_id}\n" + json.loads(info_text)["infotexts"][0]
                        else:
                            print(f"File {json_file} does not exist.")
                            info_text = 'something wrong when trying to download the inference parameters'
                            infotexts = info_text
                        return image_list, info_text, plaintext_to_html(infotexts)
                else:
                    return image_list, info_text, plaintext_to_html(infotexts)
        except Exception as e:
            print(f"Failed to get inference job {inference_id}, error: {e}")

def sagemaker_endpoint_delete(delete_endpoint_list):
    print(f"start delete sagemaker endpoint delete function")
    print(f"delete endpoint list: {delete_endpoint_list}")
    api_gateway_url = get_variable_from_json('api_gateway_url')
    api_key = get_variable_from_json('api_token')

    delete_endpoint_list = [item.split('+')[0] for item in delete_endpoint_list]
    print(f"delete endpoint list: {delete_endpoint_list}")

    # check if api_gateway_url and api_key are set
    if api_gateway_url is None or api_key is None:
        print("api_gateway_url and api_key are not set")
        return

    # Check if api_url ends with '/', if not append it
    if not api_gateway_url.endswith('/'):
        api_gateway_url += '/'

    payload = {
        "delete_endpoint_list": delete_endpoint_list,
    }

    deployment_url = f"{api_gateway_url}inference/delete-sagemaker-endpoint"

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(deployment_url, json=payload, headers=headers)
        r = response.json()
        print(f"response for rest api {r}")
        return r
    except Exception as e:
        return f"Failed to delete sagemaker endpoint with exception: {e}"


def sagemaker_deploy(instance_type, initial_instance_count=1):
    """ Create SageMaker endpoint for GPU inference.
    Args:
        instance_type (string): the ML compute instance type.
        initial_instance_count (integer): Number of instances to launch initially.
    Returns:
        (None)
    """
    # function code to call sagemaker deploy api
    print(f"start deploying instance type: {instance_type} with count {initial_instance_count}............")

    api_gateway_url = get_variable_from_json('api_gateway_url')
    api_key = get_variable_from_json('api_token')

    # check if api_gateway_url and api_key are set
    if api_gateway_url is None or api_key is None:
        print("api_gateway_url and api_key are not set")
        return
    # Check if api_url ends with '/', if not append it
    if not api_gateway_url.endswith('/'):
        api_gateway_url += '/'

    payload = {
        "instance_type": instance_type,
        "initial_instance_count": initial_instance_count
    }

    deployment_url = f"{api_gateway_url}inference/deploy-sagemaker-endpoint"

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(deployment_url, json=payload, headers=headers)
        r = response.json()
        print(f"response for rest api {r}")
        return "Endpoint deployment started"
    except Exception as e:
        return f"Failed to start endpoint deployment with exception: {e}"

def modelmerger_on_cloud_func(primary_model_name, secondary_model_name, teritary_model_name):
    print(f"function under development, current checkpoint_info is {checkpoint_info}")
    api_gateway_url = get_variable_from_json('api_gateway_url')
    # Check if api_url ends with '/', if not append it
    if not api_gateway_url.endswith('/'):
        api_gateway_url += '/'
    api_key = get_variable_from_json('api_token')

    if api_gateway_url is None:
        print(f"modelmerger: failed to get the api-gateway url, can not fetch remote data")
        return []
    modelmerge_url = f"{api_gateway_url}inference/run-model-merge"

    payload = {
        "primary_model_name" : primary_model_name,
        "secondary_model_name" : secondary_model_name,
        "tertiary_model_name" : teritary_model_name
    }

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }

    response = requests.post(modelmerge_url, json=payload, headers=headers)

    try:
        r = response.json()
    except JSONDecodeError as e:
        print(f"Failed to decode JSON response: {e}")
        print(f"Raw server response: {response.text}")
    else:
        print(f"response for rest api {r}")

def txt2img_config_save():
    # placeholder for saving txt2img config
    pass

def displayEndpointInfo(input_string: str):
    print(f"selected value is {input_string}")
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

def update_txt2imgPrompt_from_model_select(selected_items, txt2img_prompt, model_name='embeddings', with_angle_brackets=False):
    print(selected_items) #example ['FastNegativeV2.pt']
    print(txt2img_prompt)
    print(get_model_list_by_type('embeddings'))
    full_dropdown_items = get_model_list_by_type(model_name) #example ['FastNegativeV2.pt', 'okuryl3nko.pt']

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
    print(f"selected value is {selected_value}")
    print(f"original prompt is {original_prompt}")
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
                image_list = download_images(images,f"outputs/txt2img-images/{get_current_date()}/{inference_job_id}/")
                json_list = download_images(inference_pram_json_list, f"outputs/txt2img-images/{get_current_date()}/{inference_job_id}/")
                json_file = f"outputs/txt2img-images/{get_current_date()}/{inference_job_id}/{inference_job_id}_param.json"
            elif inference_job_taskType == "img2img":
                image_list = download_images(images,f"outputs/img2img-images/{get_current_date()}/{inference_job_id}/")
                json_list = download_images(inference_pram_json_list, f"outputs/img2img-images/{get_current_date()}/{inference_job_id}/")
                json_file = f"outputs/img2img-images/{get_current_date()}/{inference_job_id}/{inference_job_id}_param.json"
            print(f"{str(images)}")
            print(f"{str(inference_pram_json_list)}")
            if os.path.isfile(json_file):
                with open(json_file) as f:
                    log_file = json.load(f)
                    info_text = log_file["info"]
                    infotexts = json.loads(info_text)["infotexts"][0]
            else:
                print(f"File {json_file} does not exist.")
                info_text = 'something wrong when trying to download the inference parameters'
                infotexts = 'something wrong when trying to download the inference parameters'
        elif inference_job_taskType in ["interrogate_clip", "interrogate_deepbooru"]:
            job_status = get_inference_job(inference_job_id)
            print(job_status)
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

def display_inference_result(inference_id: str ):
    print(f"selected value is {inference_id}")
    if inference_id is not None:
        # Extract the InferenceJobId value
        inference_job_id = inference_id
        images = get_inference_job_image_output(inference_job_id)
        image_list = []
        image_list = download_images(images,f"outputs/txt2img-images/{get_current_date()}/{inference_job_id}/")

        inference_pram_json_list = get_inference_job_param_output(inference_job_id)
        json_list = []
        json_list = download_images(inference_pram_json_list, f"outputs/txt2img-images/{get_current_date()}/{inference_job_id}/")

        print(f"{str(images)}")
        print(f"{str(inference_pram_json_list)}")

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

def init_refresh_resource_list_from_cloud():
    print(f"start refreshing resource list from cloud")
    if get_variable_from_json('api_gateway_url') is not None:
        update_sagemaker_endpoints()
        refresh_all_models()
        get_texual_inversion_list()
        get_lora_list()
        get_hypernetwork_list()
        get_controlnet_model_list()
        get_inference_job_list()
    else:
        print(f"there is no api-gateway url and token in local file,")

def create_ui(is_img2img):
    global txt2img_gallery, txt2img_generation_info
    import modules.ui

    init_refresh_resource_list_from_cloud()

    with gr.Group():
        with gr.Accordion("Amazon SageMaker Inference", open=False):
            sagemaker_html_log = gr.HTML(elem_id=f'html_log_sagemaker')
            with gr.Column(variant='panel'):
                with gr.Row():
                    global sagemaker_endpoint
                    sagemaker_endpoint = gr.Dropdown(sagemaker_endpoints,
                                                     label="Select Cloud SageMaker Endpoint",
                                                     elem_id="sagemaker_endpoint_dropdown"
                                                     )

                    modules.ui.create_refresh_button(sagemaker_endpoint, update_sagemaker_endpoints, lambda: {"choices": sagemaker_endpoints}, "refresh_sagemaker_endpoints")
                with gr.Row():
                    sd_checkpoint = gr.Dropdown(multiselect=True, label="Stable Diffusion Checkpoint", choices=sorted(update_sd_checkpoints()), elem_id="stable_diffusion_checkpoint_dropdown")
                    sd_checkpoint_refresh_button = modules.ui.create_refresh_button(sd_checkpoint, update_sd_checkpoints, lambda: {"choices": sorted(update_sd_checkpoints())}, "refresh_sd_checkpoints")
            with gr.Column():
                global generate_on_cloud_button_with_js
                if not is_img2img:
                    generate_on_cloud_button_with_js = gr.Button(value="Generate on Cloud", variant='primary', elem_id="generate_on_cloud_with_cloud_config_button",queue=True, show_progress=True)
                global generate_on_cloud_button_with_js_img2img
                global interrogate_clip_on_cloud_button
                global interrogate_deep_booru_on_cloud_button
                if is_img2img:
                    with gr.Row():
                        with gr.Column():
                            interrogate_clip_on_cloud_button = gr.Button(value="Interrogate CLIP", elem_id="interrogate_clip_on_cloud_button")
                        with gr.Column():
                            interrogate_deep_booru_on_cloud_button = gr.Button(value="Interrogte DeepBooru", elem_id="interrogate_deep_booru_on_cloud_button")
                        with gr.Column():
                            generate_on_cloud_button_with_js_img2img = gr.Button(value="Generate on Cloud", variant='primary', elem_id="generate_on_cloud_with_cloud_config_button_img2img",queue=True, show_progress=True)
            with gr.Row():
                global inference_job_dropdown
                global txt2img_inference_job_ids

                inference_job_dropdown = gr.Dropdown(choices=txt2img_inference_job_ids,
                                                     label="Inference Job: Time-Type-Status-Uuid",
                                                     elem_id="txt2img_inference_job_ids_dropdown"
                                                     )
                txt2img_inference_job_ids_refresh_button = modules.ui.create_refresh_button(inference_job_dropdown, origin_update_txt2img_inference_job_ids, lambda: {"choices": txt2img_inference_job_ids}, "refresh_txt2img_inference_job_ids")
                # print(f"gr.Row() txt2img_inference_job_ids is {txt2img_inference_job_ids}")

            with gr.Row():
                with gr.Column(scale=1):
                    gr.HTML(value="Inference Job type filters")
                with gr.Column(scale=2):
                    with gr.Row():
                        task_type_choices = ["txt2img", "img2img", "interrogate_clip", "interrogate_deepbooru"]
                        task_type_dropdown = gr.Dropdown(label="Task Type", choices=task_type_choices, elem_id="task_type_ids_dropdown")
                        status_choices = ["succeed", "failure"]
                        status_dropdown = gr.Dropdown(label="Status", choices=status_choices, elem_id="task_status_dropdown")
                    with gr.Row():
                        sagemaker_endpoint_filter = gr.Dropdown(sagemaker_endpoints, label="SageMaker Endpoint", elem_id="sagemaker_endpoint_dropdown" )
                        modules.ui.create_refresh_button(sagemaker_endpoint_filter, update_sagemaker_endpoints, lambda: {"choices": sagemaker_endpoints}, "refresh_sagemaker_endpoints")
                    with gr.Row():
                        sd_checkpoint_filter = gr.Dropdown(multiselect=True, label="Checkpoint", choices=sorted(update_sd_checkpoints()), elem_id="stable_diffusion_checkpoint_dropdown")
                        modules.ui.create_refresh_button(sd_checkpoint_filter, update_sd_checkpoints, lambda: { "choices": sorted(update_sd_checkpoints())}, "refresh_sd_checkpoints")
                    if is_img2img:
                        with gr.Row():
                            stat_time_picker_img = gr.HTML(elem_id="start_timepicker_img_e",
                                                           value='<span class="svelte-1ed2p3z" style="color: #6B7280">Start Time<input type="date" lang="en" id="start_timepicker_img" min="2023-01-01" max="2033-12-31" class="wrap svelte-aqlk7e" style="color: #6B7280" onchange="inference_job_timepicker_img_change()"></span>')
                            end_time_picker_img = gr.HTML(elem_id="end_timepicker_img_e",
                                                          value='<span class="svelte-1ed2p3z" style="color: #6B7280">End Time<input type="date" lang="en" id="end_timepicker_img" min="2023-01-01" max="2033-12-31" class="wrap svelte-aqlk7e" style="color: #6B7280" onchange="inference_job_timepicker_img_change()"></span>')
                        task_type_dropdown.change(fn=query_inference_job_list,
                                                  inputs=[task_type_dropdown, status_dropdown, stat_time_picker_img,
                                                          end_time_picker_img, sagemaker_endpoint_filter,
                                                          sd_checkpoint_filter], outputs=inference_job_dropdown)
                        status_dropdown.change(fn=query_inference_job_list,
                                               inputs=[task_type_dropdown, status_dropdown, stat_time_picker_img,
                                                       end_time_picker_img, sagemaker_endpoint_filter,
                                                       sd_checkpoint_filter], outputs=inference_job_dropdown)
                        sagemaker_endpoint_filter.change(fn=query_inference_job_list,
                                                         inputs=[task_type_dropdown, status_dropdown, stat_time_picker_img,
                                                                 end_time_picker_img, sagemaker_endpoint_filter,
                                                                 sd_checkpoint_filter], outputs=inference_job_dropdown)
                        sd_checkpoint_filter.change(fn=query_inference_job_list,
                                                    inputs=[task_type_dropdown, status_dropdown, stat_time_picker_img,
                                                            end_time_picker_img, sagemaker_endpoint_filter,
                                                            sd_checkpoint_filter], outputs=inference_job_dropdown)
                    else:
                        with gr.Row():
                            stat_time_picker_text = gr.HTML(elem_id="start_timepicker_text_e",
                                                       value='<span class="svelte-1ed2p3z" style="color: #6B7280">Start Time<input type="date" lang="en" id="start_timepicker_text" min="2023-01-01" max="2033-12-31" class="wrap svelte-aqlk7e" style="color: #6B7280" onchange="inference_job_timepicker_text_change()"></span>')
                            end_time_picker_text = gr.HTML(elem_id="end_timepicker_text_e",
                                                      value='<span class="svelte-1ed2p3z" style="color: #6B7280">End Time<input type="date" lang="en" id="end_timepicker_text" min="2023-01-01" max="2033-12-31" class="wrap svelte-aqlk7e" style="color: #6B7280" onchange="inference_job_timepicker_text_change()"></span>')
                        task_type_dropdown.change(fn=query_inference_job_list,
                                                  inputs=[task_type_dropdown, status_dropdown, stat_time_picker_text,
                                                          end_time_picker_text, sagemaker_endpoint_filter,
                                                          sd_checkpoint_filter], outputs=inference_job_dropdown)
                        status_dropdown.change(fn=query_inference_job_list,
                                               inputs=[task_type_dropdown, status_dropdown, stat_time_picker_text,
                                                       end_time_picker_text, sagemaker_endpoint_filter,
                                                       sd_checkpoint_filter], outputs=inference_job_dropdown)
                        sagemaker_endpoint_filter.change(fn=query_inference_job_list,
                                                         inputs=[task_type_dropdown, status_dropdown, stat_time_picker_text,
                                                                 end_time_picker_text, sagemaker_endpoint_filter,
                                                                 sd_checkpoint_filter], outputs=inference_job_dropdown)
                        sd_checkpoint_filter.change(fn=query_inference_job_list,
                                                    inputs=[task_type_dropdown, status_dropdown, stat_time_picker_text,
                                                            end_time_picker_text, sagemaker_endpoint_filter,
                                                            sd_checkpoint_filter], outputs=inference_job_dropdown)
                #     with gr.Row():
                #         start_timepicker = gr.HTML(value='<span class="svelte-1ed2p3z" style="color: #6B7280">Start Time<input type="date" lang="en" id="start_timepicker" min="2023-01-01" max="2033-12-31" class="wrap svelte-aqlk7e" style="color: #6B7280" onchange="inference_job_timepicker_change()"></span>')
                #         end_timepicker = gr.HTML(value='<span class="svelte-1ed2p3z" style="color: #6B7280">End Time<input type="date" lang="en" id="end_timepicker" min="2023-01-01" max="2033-12-31" class="wrap svelte-aqlk7e" style="color: #6B7280" onchange="inference_job_timepicker_change()"></span>')
                # task_type_dropdown.change(fn=query_inference_job_list, inputs=[task_type_dropdown, status_dropdown, start_timepicker, end_timepicker, sagemaker_endpoint_filter, sd_checkpoint_filter], outputs=inference_job_dropdown)
                # status_dropdown.change(fn=query_inference_job_list, inputs=[task_type_dropdown, status_dropdown, start_timepicker, end_timepicker, sagemaker_endpoint_filter, sd_checkpoint_filter], outputs=inference_job_dropdown)
                # sagemaker_endpoint_filter.change(fn=query_inference_job_list, _js="inference_job_reset_time", inputs=[task_type_dropdown, status_dropdown, start_timepicker, end_timepicker, sagemaker_endpoint_filter, sd_checkpoint_filter], outputs=inference_job_dropdown)
                # sd_checkpoint_filter.change(fn=query_inference_job_list, _js="inference_job_reset_time", inputs=[task_type_dropdown, status_dropdown, start_timepicker, end_timepicker, sagemaker_endpoint_filter, sd_checkpoint_filter], outputs=inference_job_dropdown)


            with gr.Row():
                gr.HTML(value="Extra Networks for Cloud Inference")

            with gr.Row():
                global textual_inversion_dropdown
                textual_inversion_dropdown = gr.Dropdown(multiselect=True, label="Textual Inversion", choices=sorted(get_texual_inversion_list()),elem_id="sagemaker_texual_inversion_dropdown")
                create_refresh_button(
                    textual_inversion_dropdown,
                    get_texual_inversion_list,
                    lambda: {"choices": sorted(get_texual_inversion_list())},
                    "refresh_textual_inversion",
                )
                global lora_dropdown
                lora_dropdown = gr.Dropdown(lora_list,  multiselect=True, label="LoRA", elem_id="sagemaker_lora_list_dropdown")
                create_refresh_button(
                    lora_dropdown,
                    get_lora_list,
                    lambda: {"choices": sorted(get_lora_list())},
                    "refresh_lora",
                )
            with gr.Row():
                global hyperNetwork_dropdown
                hyperNetwork_dropdown = gr.Dropdown(multiselect=True, label="HyperNetwork", choices=sorted(get_hypernetwork_list()), elem_id="sagemaker_hypernetwork_dropdown")
                create_refresh_button(
                    hyperNetwork_dropdown,
                    get_hypernetwork_list,
                    lambda: {"choices": sorted(get_hypernetwork_list())},
                    "refresh_hypernetworks",
                )
                controlnet_dropdown = gr.Dropdown(multiselect=True, label="ControlNet-Model", choices=sorted(get_controlnet_model_list()), elem_id="sagemaker_controlnet_model_dropdown")
                create_refresh_button(
                    controlnet_dropdown,
                    get_controlnet_model_list,
                    lambda: {"choices": sorted(get_controlnet_model_list())},
                    "refresh_controlnet",
                )

    with gr.Group():
        with gr.Accordion("Open for Checkpoint Merge in the Cloud!", visible=False, open=False):
            sagemaker_html_log = gr.HTML(elem_id=f'html_log_sagemaker')
            with FormRow(elem_id="modelmerger_models_in_the_cloud"):
                global primary_model_name
                primary_model_name = gr.Dropdown(choices=sorted(update_sd_checkpoints()), elem_id="modelmerger_primary_model_name_in_the_cloud", label="Primary model (A) in the cloud")
                create_refresh_button(primary_model_name, update_sd_checkpoints, lambda: {"choices": sorted(update_sd_checkpoints())}, "refresh_checkpoint_A_in_the_cloud")

                global secondary_model_name
                secondary_model_name = gr.Dropdown(choices=sorted(update_sd_checkpoints()), elem_id="modelmerger_secondary_model_name_in_the_cloud", label="Secondary model (B) in the cloud")
                create_refresh_button(secondary_model_name, update_sd_checkpoints, lambda: {"choices": sorted(update_sd_checkpoints())}, "refresh_checkpoint_B_in_the_cloud")

                global tertiary_model_name
                tertiary_model_name = gr.Dropdown(choices=sorted(update_sd_checkpoints()), elem_id="modelmerger_tertiary_model_name_in_the_cloud", label="Tertiary model (C) in the cloud")
                create_refresh_button(tertiary_model_name, update_sd_checkpoints, lambda: {"choices": sorted(update_sd_checkpoints())}, "refresh_checkpoint_C_in_the_cloud")
            with gr.Row():
                global modelmerger_merge_on_cloud
                modelmerger_merge_on_cloud = gr.Button(elem_id="modelmerger_merge_in_the_cloud", value="Merge on Cloud", variant='primary')

    return sagemaker_endpoint, sd_checkpoint, sd_checkpoint_refresh_button, textual_inversion_dropdown, lora_dropdown, hyperNetwork_dropdown, controlnet_dropdown, inference_job_dropdown, txt2img_inference_job_ids_refresh_button, primary_model_name, secondary_model_name, tertiary_model_name, modelmerger_merge_on_cloud
