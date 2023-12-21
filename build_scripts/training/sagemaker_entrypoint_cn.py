import os
import re
import json
import sys
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO) # Set logging level and STDOUT handler

sys.path.insert(0, os.path.join(os.getcwd(), "extensions/stable-diffusion-aws-extension/"))
sys.path.append(os.path.join(os.getcwd(), "extensions/sd_dreambooth_extension"))
from utils import download_folder_from_s3_by_tar, download_folder_from_s3, upload_file_to_s3
from utils import get_bucket_name_from_s3_path, get_path_from_s3_path

os.environ['IGNORE_CMD_ARGS_ERRORS'] = ""
from dreambooth.ui_functions import start_training
from dreambooth.shared import status

from utils import tar, mv


def train(model_dir):
    start_training(model_dir)


def upload_model_to_s3_v2(model_name, s3_output_path, model_type, region):
    output_bucket_name = get_bucket_name_from_s3_path(s3_output_path)
    s3_output_path = get_path_from_s3_path(s3_output_path).rstrip("/")
    logger.info("Upload the model file to s3.")
    if model_type == "Stable-diffusion":
        local_path = os.path.join(f"models/{model_type}", model_name)
    elif model_type == "Lora":
        local_path = f"models/{model_type}"
    logger.info(f"Search model file in {local_path}.")
    for root, dirs, files in os.walk(local_path):
        logger.info(files)
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
                    upload_file_to_s3(output_tar, output_bucket_name, os.path.join(s3_output_path, model_name), region)
                elif model_type == "Lora":
                    output_tar = file
                    tar_command = f"tar cvf {output_tar} {safetensors}"
                    print(tar_command)
                    # os.system(tar_command)
                    tar(mode='c', archive=output_tar, sfiles=[safetensors], verbose=True)
                    print(f"Upload check point to s3 {output_tar} {output_bucket_name} {s3_output_path}")
                    upload_file_to_s3(output_tar, output_bucket_name, s3_output_path, region)


def download_data(data_list, s3_data_path_list, s3_input_path, region):
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
            download_folder_from_s3(input_bucket_name, input_path, target_dir, region)
        else:
            input_bucket_name = get_bucket_name_from_s3_path(s3_input_path)
            input_path = os.path.join(get_path_from_s3_path(s3_input_path), data_tar)
            local_tar_path = data_tar
            logger.info(f"Download data from s3 {input_bucket_name} {input_path} to {target_dir} {local_tar_path}")
            download_folder_from_s3_by_tar(input_bucket_name, input_path, local_tar_path, target_dir, region)


def prepare_for_training(s3_model_path, model_name, s3_input_path, data_tar_list, class_data_tar_list, region):
    model_bucket_name = get_bucket_name_from_s3_path(s3_model_path)
    s3_model_path = os.path.join(get_path_from_s3_path(s3_model_path), f'{model_name}.tar')
    logger.info(f"Download src model from s3: {model_bucket_name} {s3_model_path} {model_name}.tar")
    print(f"Download src model from s3: model_bucket_name __ {model_bucket_name} s3_model_path__{s3_model_path} model_name__{model_name}.tar")
    download_folder_from_s3_by_tar(model_bucket_name, s3_model_path, f'{model_name}.tar', region)

    input_bucket_name = get_bucket_name_from_s3_path(s3_input_path)
    input_path = os.path.join(get_path_from_s3_path(s3_input_path), "db_config.tar")
    logger.info(f"Download db_config from s3 {input_bucket_name} {input_path} db_config.tar")
    download_folder_from_s3_by_tar(input_bucket_name, input_path, "db_config.tar", region)
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
    download_data(data_list, data_tar_list, s3_input_path, region)
    download_data(class_data_list, class_data_tar_list, s3_input_path, region)


def main(s3_input_path, s3_output_path, params, region):
    os.system("df -h")
    # import launch
    # launch.prepare_environment()
    model_name = params["model_name"]
    model_type = params["model_type"]
    s3_model_path = params["s3_model_path"]
    s3_data_path_list = params["data_tar_list"]
    s3_class_data_path_list = params["class_data_tar_list"]
    # s3_data_path_list = params["s3_data_path_list"]
    # s3_class_data_path_list = params["s3_class_data_path_list"]
    print(f"s3_model_path {s3_model_path} model_name:{model_name} s3_input_path: {s3_input_path} s3_data_path_list:{s3_data_path_list} s3_class_data_path_list:{s3_class_data_path_list}")
    prepare_for_training(s3_model_path, model_name, s3_input_path, s3_data_path_list, s3_class_data_path_list, region)
    os.system("df -h")
    # sync_status(job_id, bucket_name, model_dir)
    train(model_name)
    os.system("df -h")
    os.system("ls -R models")
    upload_model_to_s3_v2(model_name, s3_output_path, model_type)
    os.system("df -h")


if __name__ == "__main__":
    print(sys.argv)
    command_line_args = ' '.join(sys.argv[1:])
    params = {}
    s3_input_path = ''
    s3_output_path = ''
    args_list = command_line_args.split("--")
    for arg in args_list:
        if arg.strip().startswith("params"):
            start_idx = arg.find("{")
            end_idx = arg.rfind("}")
            if start_idx != -1 and end_idx != -1:
                params_str = arg[start_idx:end_idx+1]
                try:
                    params_str = params_str.replace(" ", "").replace("\n", "").replace("'", "")
                    print(params_str)
                    params_str = params_str.replace(",,", ",")
                    print(params_str)
                    params_str = params_str.replace(",,", ",")
                    print(params_str)
                    fixed_string = params_str.replace('{', '{"').replace(':', '":"').replace(',', '","')\
                        .replace('}', '"}').replace("\"[", "[\"").replace("]\"", "\"]").replace('s3":"//', "s3://")
                    print(fixed_string)
                    params = json.loads(fixed_string)
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e}")
        if arg.strip().startswith("s3-input-path"):
            start_idx = arg.find(":")
            s3_input_path = f"s3{arg[start_idx:]}"
        if arg.strip().startswith("s3-output-path"):
            start_idx = arg.find(":")
            s3_output_path = f"s3{arg[start_idx:]}"
    training_params = params
    print(training_params)
    print(s3_input_path)
    print(s3_output_path)
    region = 'cn-northwest-1'
    main(s3_input_path, s3_output_path, training_params, region)