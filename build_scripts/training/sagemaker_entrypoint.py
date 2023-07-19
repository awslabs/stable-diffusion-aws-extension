import os
import re
import json
import threading
import sys
import time
import pickle
import logging
import base64
logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO) # Set logging level and STDOUT handler

import boto3

sys.path.insert(0, os.path.join(os.getcwd(), "extensions/stable-diffusion-aws-extension/"))
sys.path.append(os.path.join(os.getcwd(), "extensions/sd_dreambooth_extension"))
from utils import download_file_from_s3, download_folder_from_s3_by_tar, download_folder_from_s3, upload_file_to_s3, upload_folder_to_s3_by_tar
from utils import get_bucket_name_from_s3_path, get_path_from_s3_path

os.environ['IGNORE_CMD_ARGS_ERRORS'] = ""
from dreambooth.ui_functions import start_training
from dreambooth.shared import status

from utils import tar, mv

def sync_status_from_s3_json(bucket_name, webui_status_file_path, sagemaker_status_file_path):
    while True:
        time.sleep(1)
        print(f'sagemaker status: {status.__dict__}')
        try:
            download_file_from_s3(bucket_name, webui_status_file_path, 'webui_status.json')
            with open('webui_status.json') as webui_status_file:
                webui_status = json.load(webui_status_file)
            status.do_save_model = webui_status['do_save_model']
            status.do_save_samples = webui_status['do_save_samples']
            status.interrupted = webui_status['interrupted']
            status.interrupted_after_save = webui_status['interrupted_after_save']
            status.interrupted_after_epoch =  webui_status['interrupted_after_epoch']
        except Exception as e:
            print('The webui status file is not exists')
            print(e)
        with open('sagemaker_status.json', 'w') as sagemaker_status_file:
            json.dump(status.__dict__, sagemaker_status_file)
        upload_file_to_s3('sagemaker_status.json', bucket_name, sagemaker_status_file_path)

def sync_status_from_s3_in_sagemaker(bucket_name, webui_status_file_path, sagemaker_status_file_path):
    while True:
        time.sleep(1)
        print(status.__dict__)
        try:
            download_file_from_s3(bucket_name, webui_status_file_path, 'webui_status.pickle')
            with open('webui_status.pickle', 'rb') as webui_status_file:
                webui_status = pickle.load(webui_status_file)
            status.do_save_model = webui_status['do_save_model']
            status.do_save_samples = webui_status['do_save_samples']
            status.interrupted = webui_status['interrupted']
            status.interrupted_after_save = webui_status['interrupted_after_save']
            status.interrupted_after_epoch =  webui_status['interrupted_after_epoch']
        except Exception as e:
            print('The webui status file is not exists')
            print(f'error: {e}')
        with open('sagemaker_status.pickle', 'wb') as sagemaker_status_file:
            pickle.dump(status, sagemaker_status_file)
        upload_file_to_s3('sagemaker_status.pickle', bucket_name, sagemaker_status_file_path)

def train(model_dir):
    start_training(model_dir)

def check_and_upload(local_path, bucket, s3_path):
    while True:
        time.sleep(1)
        if os.path.exists(local_path):
            print(f'upload {s3_path} to {local_path}')
            upload_folder_to_s3_by_tar(local_path, bucket, s3_path)
        else:
            print(f'{local_path} is not exist')

def upload_model_to_s3(model_name, s3_output_path):
    output_bucket_name = get_bucket_name_from_s3_path(s3_output_path)
    local_path = os.path.join("models/Stable-diffusion", model_name)
    s3_output_path = get_path_from_s3_path(s3_output_path)
    logger.info(f"Upload check point to s3 {local_path} {output_bucket_name} {s3_output_path}")
    print(f"Upload check point to s3 {local_path} {output_bucket_name} {s3_output_path}")
    upload_folder_to_s3_by_tar(local_path, output_bucket_name, s3_output_path)

def upload_model_to_s3_v2(model_name, s3_output_path, model_type):
    output_bucket_name = get_bucket_name_from_s3_path(s3_output_path)
    s3_output_path = get_path_from_s3_path(s3_output_path).rstrip("/")
    logger.info("Upload the model file to s3.")
    if model_type == "Stable-diffusion":
        local_path = os.path.join(f"models/{model_type}", model_name)
    elif model_type == "Lora":
        local_path = f"models/{model_type}"
    for root, dirs, files in os.walk(local_path):
        for file in files:
            if file.endswith('.safetensors'):
                ckpt_name = re.sub('\.safetensors$', '', file)
                safetensors = os.path.join(root, file)
                print(f'model type: {model_type}')
                if model_type == "Stable-diffusion":
                    yaml = os.path.join(root, f"{ckpt_name}.yaml")
                    output_tar = file
                    tar_command = f"tar cvf {output_tar} {safetensors} {yaml}"
                    print(tar_command)
                    # os.system(tar_command)
                    tar(mode='c', archive=output_tar, sfiles=[safetensors, yaml], verbose=True)
                    print(f"Upload check point to s3 {output_tar} {output_bucket_name} {s3_output_path}")
                    upload_file_to_s3(output_tar, output_bucket_name, os.path.join(s3_output_path, model_name))
                elif model_type == "Lora":
                    output_tar = file
                    tar_command = f"tar cvf {output_tar} {safetensors}"
                    print(tar_command)
                    # os.system(tar_command)
                    tar(mode='c', archive=output_tar, sfiles=[safetensors], verbose=True)
                    print(f"Upload check point to s3 {output_tar} {output_bucket_name} {s3_output_path}")
                    upload_file_to_s3(output_tar, output_bucket_name, s3_output_path)


def download_data(data_list, s3_data_path_list, s3_input_path):
    for data, data_tar in zip(data_list, s3_data_path_list):
        if len(data) == 0:
            continue
        target_dir = data
        os.makedirs(target_dir, exist_ok=True)
        if data_tar.startswith("s3://"):
            input_bucket_name = get_bucket_name_from_s3_path(data_tar)
            input_path = get_path_from_s3_path(data_tar)
            local_tar_path = data_tar.replace("s3://", "").replace("/", "-")
            logger.info(f"Download data from s3 {input_bucket_name} {input_path} to {target_dir} {local_tar_path}")
            download_folder_from_s3(input_bucket_name, input_path, target_dir)
        else:
            input_bucket_name = get_bucket_name_from_s3_path(s3_input_path)
            input_path = os.path.join(get_path_from_s3_path(s3_input_path), data_tar)
            local_tar_path = data_tar
            logger.info(f"Download data from s3 {input_bucket_name} {input_path} to {target_dir} {local_tar_path}")
            download_folder_from_s3_by_tar(input_bucket_name, input_path, local_tar_path, target_dir)

def prepare_for_training(s3_model_path, model_name, s3_input_path, data_tar_list, class_data_tar_list):
    model_bucket_name = get_bucket_name_from_s3_path(s3_model_path)
    s3_model_path = os.path.join(get_path_from_s3_path(s3_model_path), f'{model_name}.tar')
    logger.info(f"Download src model from s3 {model_bucket_name} {s3_model_path} {model_name}.tar")
    print(f"Download src model from s3 {model_bucket_name} {s3_model_path} {model_name}.tar")
    download_folder_from_s3_by_tar(model_bucket_name, s3_model_path, f'{model_name}.tar')

    input_bucket_name = get_bucket_name_from_s3_path(s3_input_path)
    input_path = os.path.join(get_path_from_s3_path(s3_input_path), "db_config.tar")
    logger.info(f"Download db_config from s3 {input_bucket_name} {input_path} db_config.tar")
    download_folder_from_s3_by_tar(input_bucket_name, input_path, "db_config.tar")
    download_db_config_path = f"models/sagemaker_dreambooth/{model_name}/db_config_cloud.json"
    target_db_config_path = f"models/dreambooth/{model_name}/db_config.json"
    logger.info(f"Move db_config to correct position {download_db_config_path} {target_db_config_path}")
    # os.system(f"mv {download_db_config_path} {target_db_config_path}")
    mv(download_db_config_path, target_db_config_path, force=True)
    with open(target_db_config_path) as db_config_file:
        db_config = json.load(db_config_file)
        logger.info(db_config)
    data_list = []
    class_data_list = []
    for concept in db_config["concepts_list"]:
        data_list.append(concept["instance_data_dir"])
        class_data_list.append(concept["class_data_dir"])
    # hack_db_config(db_config, db_config_path, model_name, data_tar_list, class_data_tar_list)
    download_data(data_list, data_tar_list, s3_input_path)
    download_data(class_data_list, class_data_tar_list, s3_input_path)

def prepare_for_training_v2(s3_model_path, model_name, s3_input_path, s3_data_path_list, s3_class_data_path_list):
    model_bucket_name = get_bucket_name_from_s3_path(s3_model_path)
    s3_model_path = os.path.join(get_path_from_s3_path(s3_model_path), f'{model_name}.tar')
    logger.info(f"Download src model from s3 {model_bucket_name} {s3_model_path} {model_name}.tar")
    print(f"Download src model from s3 {model_bucket_name} {s3_model_path} {model_name}.tar")
    download_folder_from_s3_by_tar(model_bucket_name, s3_model_path, f'{model_name}.tar')

    # input_bucket_name = get_bucket_name_from_s3_path(s3_input_path)
    input_path = os.path.join(get_path_from_s3_path(s3_input_path), "db_config.tar")
    logger.info(f"Download db_config from s3 {input_bucket_name} {input_path} db_config.tar")
    download_folder_from_s3_by_tar(input_bucket_name, input_path, "db_config.tar")
    download_db_config_path = f"models/sagemaker_dreambooth/{model_name}/db_config_cloud.json"
    target_db_config_path = f"models/dreambooth/{model_name}/db_config.json"
    logger.info(f"Move db_config to correct position {download_db_config_path} {target_db_config_path}")
    # os.system(f"mv {download_db_config_path} {target_db_config_path}")
    mv(download_db_config_path, target_db_config_path)
    with open(target_db_config_path) as db_config_file:
        db_config = json.load(db_config_file)
    data_list = []
    class_data_list = []
    for concept in db_config["concepts_list"]:
        data_list.append(concept["instance_data_dir"])
        class_data_list.append(concept["class_data_dir"])
    # hack_db_config(db_config, db_config_path, model_name, data_tar_list, class_data_tar_list)

    for s3_data_path, local_data_path in zip(data_list, s3_data_path_list):
        if len(local_data_path) == 0:
            continue
        target_dir = local_data_path
        os.makedirs(target_dir, exist_ok=True)
        input_bucket_name = get_bucket_name_from_s3_path(s3_data_path)
        input_path = get_path_from_s3_path(s3_data_path)
        logger.info(f"Download data from s3 {input_bucket_name} {input_path} to {target_dir}")
        download_folder_from_s3_by_tar(input_bucket_name, input_path, target_dir)
    for s3_class_data_path, local_class_data_path in zip(class_data_list, s3_class_data_path_list):
        if len(local_class_data_path) == 0:
            continue
        target_dir = local_class_data_path
        os.makedirs(target_dir, exist_ok=True)
        input_bucket_name = get_bucket_name_from_s3_path(s3_class_data_path)
        input_path = get_path_from_s3_path(s3_class_data_path)
        logger.info(f"Download data from s3 {input_bucket_name} {input_path} to {target_dir}")
        download_folder_from_s3_by_tar(input_bucket_name, input_path, target_dir)

def sync_status(job_id, bucket_name, model_dir):
    local_samples_dir = f'models/dreambooth/{model_dir}/samples'
    upload_thread = threading.Thread(target=check_and_upload, args=(local_samples_dir, bucket_name, f'aigc-webui-test-samples/{job_id}'))
    upload_thread.start()
    sync_status_thread = threading.Thread(target=sync_status_from_s3_in_sagemaker,
                                        args=(bucket_name, f'aigc-webui-test-status/{job_id}/webui_status.pickle',
                                              f'aigc-webui-test-status/{job_id}/sagemaker_status.pickle'))
    sync_status_thread.start()

def main(s3_input_path, s3_output_path, params):
    os.system("df -h")
    import launch
    launch.prepare_environment()
    params = params["training_params"]
    model_name = params["model_name"]
    model_type = params["model_type"]
    s3_model_path = params["s3_model_path"]
    s3_data_path_list = params["data_tar_list"]
    s3_class_data_path_list = params["class_data_tar_list"]
    # s3_data_path_list = params["s3_data_path_list"]
    # s3_class_data_path_list = params["s3_class_data_path_list"]
    prepare_for_training(s3_model_path, model_name, s3_input_path, s3_data_path_list, s3_class_data_path_list)
    os.system("df -h")
    # sync_status(job_id, bucket_name, model_dir)
    train(model_name)
    os.system("df -h")
    upload_model_to_s3_v2(model_name, s3_output_path, model_type)
    os.system("df -h")

def test():
    model_name = "qiaohu-1-1"
    s3_model_path = "s3://stable-diffusion-aws-5c2b588b-2023-05-19-02/Stable-diffusion/model/qiaohu-1-1/066dc5e6-1ed7-470a-ab9e-aa9e01cfe5e4/output"
    s3_input_path = "s3://stable-diffusion-aws-5c2b588b-2023-05-19-02/Stable-diffusion/train/qiaohu-1-1/546290f8-9b0c-460b-be28-74a4ccad9a63/input"
    s3_output_path = "s3://stable-diffusion-aws-5c2b588b-2023-05-19-02/Stable-diffusion/model/qiaohu-1-1/066dc5e6-1ed7-470a-ab9e-aa9e01cfe5e4/output"
    training_params = {
        "training_params": {
            "model_name": model_name,
            "s3_model_path": s3_model_path,
            "data_tar_list": ["data_images-75.tar"],
            "class_data_tar_list": [""],
        }
    }
    main(s3_input_path, s3_output_path, training_params)

def parse_params(args):
    def decode_base64(base64_message):
        base64_bytes = base64_message.encode('ascii')
        message_bytes = base64.b64decode(base64_bytes)
        message = message_bytes.decode('ascii')
        return message
    s3_input_path = json.loads(decode_base64(args.s3_input_path))
    s3_output_path = json.loads(decode_base64(args.s3_output_path))
    params = json.loads(decode_base64(args.params))
    return s3_input_path, s3_output_path, params

if __name__ == "__main__":
    # test()
    # sys.exit()
    print(sys.argv)
    import argparse
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--params", type=str)
    parser.add_argument("--s3-input-path", type=str)
    parser.add_argument("--s3-output-path", type=str)
    args, _ = parser.parse_known_args()
    s3_input_path, s3_output_path, training_params = parse_params(args)
    main(s3_input_path, s3_output_path, training_params)

    # upload_model_to_s3_v2("test-1-1", "s3://stable-diffusion-aws-extension-991301791329-us-east-1/dreambooth/checkpoint/test-sd-type/test/")