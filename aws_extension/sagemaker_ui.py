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

inference_job_dropdown = None
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


def update_txt2img_inference_job_ids():
    global txt2img_inference_job_ids
    get_inference_job_list()

def origin_update_txt2img_inference_job_ids():
    global origin_txt2img_inference_job_ids

def get_inference_job_list():
    global txt2img_inference_job_ids
    try:
        txt2img_inference_job_ids.clear()  # Clear the existing list before appending new values
        response = server_request('inference/list-inference-jobs')
        r = response.json()
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

            # Sort the list based on completeTime in descending order
            sorted_list = sorted(temp_list, key=lambda x: x[0], reverse=True)

            # Append the sorted combined strings to the txt2img_inference_job_ids list
            for item in sorted_list:
                txt2img_inference_job_ids.append(item[1])

        else:
            print("The API response is empty.")
    except Exception as e:
        print("Exception occurred when fetching inference_job_ids")



def get_inference_job(inference_job_id):
    response = server_request(f'inference/get-inference-job?jobID={inference_job_id}')
    print(f"response of get_inference_job is {str(response)}")
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
                    ckpt_s3_pos = f"{ckpt['s3Location']}/{ckpt_name.split('/')[-1]}"
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
        model_name = lp.split("/")[-1]

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
                local_model_path_in_repo = f'models/{rp}/{model_name}'
            else:
                local_model_path_in_repo = f'{rp}/{model_name}'
            #local_tar_path = f'{model_name}.tar'
            print("Pack the model file.")
            os.system(f"cp -f {lp} {local_model_path_in_repo}")
            if rp == "Stable-diffusion":
                model_yaml_name = model_name.split('.')[0] + ".yaml"
                local_model_yaml_path = "/".join(lp.split("/")[:-1]) + f"/{model_yaml_name}"
                local_model_yaml_path_in_repo = f"models/{rp}/{model_yaml_name}"
                if os.path.isfile(local_model_yaml_path):
                    os.system(f"cp -f {local_model_yaml_path} {local_model_yaml_path_in_repo}")
                    os.system(f"tar cvf {local_tar_path} {local_model_path_in_repo} {local_model_yaml_path_in_repo}")
                else:
                    os.system(f"tar cvf {local_tar_path} {local_model_path_in_repo}")
            else:
                os.system(f"tar cvf {local_tar_path} {local_model_path_in_repo}")
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

            os.system(f"rm {local_tar_path}")
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

def call_txt2img_inference(sagemaker_endpoint):
    return call_remote_inference(sagemaker_endpoint, 'txt2img')

def call_img2img_inference(endpoint_value, init_img, sketch, init_img_with_mask, inpaint_color_sketch, init_img_inpaint, init_mask_inpaint):
    return call_remote_inference(endpoint_value, 'img2img')

def call_interrogate_clip(sagemaker_endpoint, init_img, sketch, init_img_with_mask, inpaint_color_sketch, init_img_inpaint, init_mask_inpaint):
    return call_remote_inference(sagemaker_endpoint, 'interrogate_clip')

def call_interrogate_deepbooru(sagemaker_endpoint, init_img, sketch, init_img_with_mask, inpaint_color_sketch, init_img_inpaint, init_mask_inpaint):
    return call_remote_inference(sagemaker_endpoint, 'interrogate_deepbooru')


def call_remote_inference(sagemaker_endpoint, type):
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
        print(f"response for rest api {r}")
        inference_id = r.get('inference_id')  # Assuming the response contains 'inference_id' field
        print(f"inference_id is {inference_id}")

        image_list = []  # Return an empty list if selected_value is None
        info_text = ''
        infotexts = f"Inference id is {inference_id}, please go to inference job Id dropdown to check the status"
        return image_list, info_text, plaintext_to_html(infotexts)

        # TODO: temp comment the while loop since it will block user to click inference
        # # Loop until the get_inference_job status is 'succeed' or 'failed'
        # max_attempts = 10
        # attempt_count = 0
        # while attempt_count < max_attempts:
        #     job_status = get_inference_job(inference_id)
        #     status = job_status['status']
        #     if status == 'succeed':
        #         break
        #     elif status == 'failure':
        #         print(f"Inference job failed: {job_status.get('error', 'No error message provided')}")
        #         break
        #     time.sleep(3)  # You can adjust the sleep time as needed
        #     attempt_count += 1

        # if status == 'succeed':
        #     return display_inference_result(inference_id)
        # elif status == 'failure':
        #     image_list = []  # Return an empty list if selected_value is None
        #     info_text = ''
        #     infotexts = f"Inference Failed! The error info: {job_status.get('error', 'No error message provided')}"
        #     return image_list, info_text, plaintext_to_html(infotexts)
        # else:
        #     image_list = []  # Return an empty list if selected_value is None
        #     info_text = ''
        #     infotexts = f"Inference time is longer than 30 seconds, please go to inference job Id dropdown to check the status"
        #     return image_list, info_text, plaintext_to_html(infotexts)

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
        return "Endpoint delete completed"
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

def fake_gan(selected_value: str ):
    print(f"selected value is {selected_value}")
    if selected_value is not None:
        delimiter = "-->"
        parts = selected_value.split(delimiter)
        # Extract the InferenceJobId value
        inference_job_id = parts[2].strip()
        inference_job_status = parts[1].strip()
        if inference_job_status == 'inprogress':
            return [], [], plaintext_to_html('inference still in progress')
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
                            generate_on_cloud_button_with_js_img2img = gr.Button(value="Generate on Cloud img2img", variant='primary', elem_id="generate_on_cloud_with_cloud_config_button_img2img",queue=True, show_progress=True)
            with gr.Row():
                global inference_job_dropdown
                global txt2img_inference_job_ids
                inference_job_dropdown = gr.Dropdown(txt2img_inference_job_ids,
                                                     label="Inference Job IDs",
                                                     elem_id="txt2img_inference_job_ids_dropdown"
                                                     )
                txt2img_inference_job_ids_refresh_button = modules.ui.create_refresh_button(inference_job_dropdown, update_txt2img_inference_job_ids, lambda: {"choices": txt2img_inference_job_ids}, "refresh_txt2img_inference_job_ids")

            with gr.Row():
                gr.HTML(value="Extra Networks for Cloud Inference")

            with gr.Row():
                textual_inversion_dropdown = gr.Dropdown(multiselect=True, label="Textual Inversion", choices=sorted(get_texual_inversion_list()),elem_id="sagemaker_texual_inversion_dropdown")
                create_refresh_button(
                    textual_inversion_dropdown,
                    get_texual_inversion_list,
                    lambda: {"choices": sorted(get_texual_inversion_list())},
                    "refresh_textual_inversion",
                )
                lora_dropdown = gr.Dropdown(lora_list,  multiselect=True, label="LoRA", elem_id="sagemaker_lora_list_dropdown")
                create_refresh_button(
                    lora_dropdown,
                    get_lora_list,
                    lambda: {"choices": sorted(get_lora_list())},
                    "refresh_lora",
                )
            with gr.Row():
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
