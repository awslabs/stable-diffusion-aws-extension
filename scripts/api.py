import hashlib
import json
import logging
import os
import traceback
import time
import copy

import requests
from fastapi import FastAPI

from modules import sd_models
import modules.extras
import sys
from aws_extension.models import InvocationsRequest
from aws_extension.mme_utils import checkspace_and_update_models, download_model, models_path
import requests
from utils import get_bucket_name_from_s3_path, get_path_from_s3_path, download_folder_from_s3_by_tar, \
    upload_folder_to_s3_by_tar, read_from_s3

dreambooth_available = True
THREAD_CHECK_COUNT = 1
CONDITION_POOL_MAX_COUNT = 10
CONDITION_WAIT_TIME_OUT = 100000


def dummy_function(*args, **kwargs):
    return None

try:
    sys.path.append("extensions/sd_dreambooth_extension")
    from dreambooth.ui_functions import create_model
except Exception as e:
    logging.warning("[api]Dreambooth is not installed or can not be imported, using dummy function to proceed.")
    dreambooth_available = False
    create_model = dummy_function

logger = logging.getLogger(__name__)

if os.environ.get("DEBUG_API", False):
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

def merge_model_on_cloud(req):
    def modelmerger(*args):
        try:
            results = modules.extras.run_modelmerger(*args)
        except Exception as e:
            logger.info(f"Error loading/saving model file: {e}")
            logger.info(traceback.format_exc(), file=sys.stderr)
            # modules.sd_models.list_models()  # to remove the potentially missing models from the list
            return [None, None, None, None, f"Error merging checkpoints: {e}"]
        return results

    merge_checkpoint_payload = req.merge_checkpoint_payload
    primary_model_name = merge_checkpoint_payload["primary_model_name"]
    secondary_model_name = merge_checkpoint_payload["secondary_model_name"]
    tertiary_model_name = merge_checkpoint_payload["teritary_model_name"]
    interp_method = merge_checkpoint_payload["interp_method"]
    interp_amount = merge_checkpoint_payload["interp_amount"]
    save_as_half = merge_checkpoint_payload["save_as_half"]
    custom_name = merge_checkpoint_payload["custom_name"]
    checkpoint_format = merge_checkpoint_payload["checkpoint_format"]
    config_source = merge_checkpoint_payload["config_source"]
    bake_in_vae = merge_checkpoint_payload["bake_in_vae"]
    discard_weights = merge_checkpoint_payload["discard_weights"]
    save_metadata = merge_checkpoint_payload["save_metadata"]
    merge_model_s3_pos = merge_checkpoint_payload["merge_model_s3"]

    # upload checkpoints from cloud to local variable
    model_type = 'Stable-diffusion'
    checkpoint_info = req.checkpoint_info
    selected_model_s3_pos = checkpoint_info[model_type][primary_model_name]
    download_model(primary_model_name, selected_model_s3_pos)
    selected_model_s3_pos = checkpoint_info[model_type][secondary_model_name]
    download_model(secondary_model_name, selected_model_s3_pos)
    if tertiary_model_name:
        selected_model_s3_pos = checkpoint_info[model_type][tertiary_model_name]
        download_model(tertiary_model_name, selected_model_s3_pos)

    sd_models.list_models()

    for model_name in sd_models.checkpoints_list.keys():
        raw_name = model_name[:-13]
        if raw_name == primary_model_name:
            primary_model_name = model_name
        if raw_name == secondary_model_name:
            secondary_model_name = model_name
        if raw_name == tertiary_model_name:
            tertiary_model_name = model_name

    logger.info(f"sd model checkpoint list is {sd_models.checkpoints_list}")

    [primary_model_name, secondary_model_name, tertiary_model_name, component_dict_sd_model_checkpoints, modelmerger_result] = \
        modelmerger("fake_id_task", primary_model_name, secondary_model_name, tertiary_model_name, \
        interp_method, interp_amount, save_as_half, custom_name, checkpoint_format, config_source, \
        bake_in_vae, discard_weights, save_metadata)

    output_model_position = modelmerger_result[20:]

    # check whether yaml exists
    merge_model_name = output_model_position.split('/')[-1].replace(' ','\ ')

    yaml_position = output_model_position[:-len(output_model_position.split('.')[-1])]+'yaml'
    yaml_states = os.path.isfile(yaml_position)

    new_merge_model_name = merge_model_name.replace('(','_').replace(')','_')

    base_path = models_path[model_type]

    merge_model_name_complete_path = base_path + '/' + merge_model_name
    new_merge_model_name_complete_path = base_path + '/' + new_merge_model_name
    merge_model_name_complete_path = merge_model_name_complete_path.replace('(','\(').replace(')','\)')
    os.system(f"mv {merge_model_name_complete_path} {new_merge_model_name_complete_path}")

    model_yaml = (merge_model_name[:-len(merge_model_name.split('.')[-1])]+'yaml').replace('(','\(').replace(')','\)')
    model_yaml_complete_path = base_path + '/' + model_yaml

    logger.info(f"m {merge_model_name_complete_path}, n_m {new_merge_model_name_complete_path}, yaml {model_yaml_complete_path}")

    if yaml_states:
        new_model_yaml = model_yaml.replace('(','_').replace(')','_')
        new_model_yaml_complete_path = base_path + '/' + new_model_yaml
        os.system(f"mv {model_yaml_complete_path} {new_model_yaml_complete_path}")
        os.system(f"tar cvf {new_merge_model_name} {new_merge_model_name_complete_path} {new_model_yaml_complete_path}")
    else:
        os.system(f"tar cvf {new_merge_model_name} {new_merge_model_name_complete_path} ")

    os.system(f'./tools/s5cmd cp {new_merge_model_name} {merge_model_s3_pos}{new_merge_model_name}')
    os.system(f'rm {new_merge_model_name_complete_path}')
    os.system(f'rm {new_model_yaml_complete_path}')

    logger.info(f"output model path is {output_model_position}")

    return output_model_position


def sagemaker_api(_, app: FastAPI):
    logger.debug("Loading Sagemaker API Endpoints.")
    import threading
    from collections import deque
    global condition
    condition = threading.Condition()
    global thread_deque
    thread_deque = deque()

    @app.post("/invocations")
    def invocations(req: InvocationsRequest):
        """
        Check the current state of Dreambooth processes.
        @return:
        """
        logger.info('-------invocation------')

        def show_slim_dict(payload):
            pay_type = type(payload)
            if pay_type is dict:
                for k, v in payload.items():
                    logger.info(f"{k}")
                    show_slim_dict(v)
            elif pay_type is list:
                for v in payload:
                    logger.info(f"list")
                    show_slim_dict(v)
            elif pay_type is str:
                if len(payload) > 50:
                    logger.info(f" : {len(payload)} contents")
                else:
                    logger.info(f" : {payload}")
            else:
                logger.info(f" : {payload}")

        with condition:
            try:
                thread_deque.append(req)
                logger.info(f"{threading.current_thread().ident}_{threading.current_thread().name} {len(thread_deque)}")
                if len(thread_deque) > THREAD_CHECK_COUNT and len(thread_deque) <= CONDITION_POOL_MAX_COUNT:
                    logger.info(f"wait {threading.current_thread().ident}_{threading.current_thread().name} {len(thread_deque)}")
                    condition.wait(timeout=CONDITION_WAIT_TIME_OUT)
                elif len(thread_deque) > CONDITION_POOL_MAX_COUNT:
                    logger.info(f"waiting thread too much in condition pool {len(thread_deque)}, max: {CONDITION_POOL_MAX_COUNT}")
                    raise MemoryError

                logger.info(f"task is {req.task}")
                logger.info(f"models is {req.models}")
                payload = {}
                if req.param_s3:
                    def parse_constant(c: str) -> float:
                        if c == "NaN":
                            raise ValueError("NaN is not valid JSON")

                        if c == 'Infinity':
                            return sys.float_info.max

                        return float(c)

                    payload = json.loads(read_from_s3(req.param_s3), parse_constant=parse_constant)
                    show_slim_dict(payload)

                logger.info(f"extra_single_payload is: ")
                extra_single_payload = {} if req.extras_single_payload is None else json.loads(
                    req.extras_single_payload.json())
                show_slim_dict(extra_single_payload)
                logger.info(f"extra_batch_payload is: ")
                extra_batch_payload = {} if req.extras_batch_payload is None else json.loads(
                    req.extras_batch_payload.json())
                show_slim_dict(extra_batch_payload)
                logger.info(f"interrogate_payload is: ")
                interrogate_payload = {} if req.interrogate_payload is None else json.loads(req.interrogate_payload.json())
                show_slim_dict(interrogate_payload)

                if req.task == 'txt2img':
                    logger.info(f"{threading.current_thread().ident}_{threading.current_thread().name}_______ txt2img start !!!!!!!!")
                    checkspace_and_update_models(req.models)
                    logger.info(f"{threading.current_thread().ident}_{threading.current_thread().name}_______ txt2img models update !!!!!!!!")
                    response = requests.post(url=f'http://0.0.0.0:8080/sdapi/v1/txt2img',
                                             json=payload)
                    logger.info(f"{threading.current_thread().ident}_{threading.current_thread().name}_______ txt2img end !!!!!!!! {len(response.json())}")
                    return response.json()
                elif req.task == 'img2img':
                    logger.info(f"{threading.current_thread().ident}_{threading.current_thread().name}_______ img2img start!!!!!!!!")
                    checkspace_and_update_models(req.models)
                    logger.info(f"{threading.current_thread().ident}_{threading.current_thread().name}_______ txt2img models update !!!!!!!!")
                    response = requests.post(url=f'http://0.0.0.0:8080/sdapi/v1/img2img',
                                             json=payload)
                    logger.info(f"{threading.current_thread().ident}_{threading.current_thread().name}_______ img2img end !!!!!!!!{len(response.json())}")
                    return response.json()
                elif req.task == 'interrogate_clip' or req.task == 'interrogate_deepbooru':
                    response = requests.post(url=f'http://0.0.0.0:8080/sdapi/v1/interrogate',
                                             json=json.loads(req.interrogate_payload.json()))
                    return response.json()
                elif req.task == 'extra-single-image':
                    response = requests.post(url=f'http://0.0.0.0:8080/sdapi/v1/extra-single-image',
                                             json=payload)
                    return response.json()
                elif req.task == 'extra-batch-images':
                    response = requests.post(url=f'http://0.0.0.0:8080/sdapi/v1/extra-batch-images',
                                             json=payload)
                    return response.json()
                elif req.task == 'rembg':
                    response = requests.post(url=f'http://0.0.0.0:8080/rembg', json=payload)
                    return response.json()
                elif req.task == 'db-create-model':
                    r"""
                    task: db-create-model
                    db_create_model_payload:
                        :s3_input_path: S3 path for download src model.
                        :s3_output_path: S3 path for upload generated model.
                        :ckpt_from_cloud: Whether to get ckpt from cloud or local.
                        :job_id: job id.
                        :param
                            :new_model_name: generated model name.
                            :ckpt_path: S3 path for download src model.
                            :db_new_model_shared_src="",
                            :from_hub=False,
                            :new_model_url="",
                            :new_model_token="",
                            :extract_ema=False,
                            :train_unfrozen=False,
                            :is_512=True,
                    """
                    try:
                        db_create_model_payload = json.loads(req.db_create_model_payload)
                        job_id = db_create_model_payload["job_id"]
                        s3_output_path = db_create_model_payload["s3_output_path"]
                        output_bucket_name = get_bucket_name_from_s3_path(s3_output_path)
                        output_path = get_path_from_s3_path(s3_output_path)
                        db_create_model_params = db_create_model_payload["param"]["create_model_params"]
                        if "ckpt_from_cloud" in db_create_model_payload["param"]:
                            ckpt_from_s3 = db_create_model_payload["param"]["ckpt_from_cloud"]
                        else:
                            ckpt_from_s3 = False
                        if not db_create_model_params['from_hub']:
                            if ckpt_from_s3:
                                s3_input_path = db_create_model_payload["param"]["s3_ckpt_path"]
                                local_model_path = db_create_model_params["ckpt_path"]
                                input_path = get_path_from_s3_path(s3_input_path)
                                logger.info(f"ckpt from s3 {input_path} {local_model_path}")
                            else:
                                s3_input_path = db_create_model_payload["s3_input_path"]
                                local_model_path = db_create_model_params["ckpt_path"]
                                input_path = os.path.join(get_path_from_s3_path(s3_input_path), local_model_path)
                                logger.info(f"ckpt from local {input_path} {local_model_path}")
                            input_bucket_name = get_bucket_name_from_s3_path(s3_input_path)
                            logging.info("Check disk usage before download.")
                            os.system("df -h")
                            logger.info(f"Download src model from s3 {input_bucket_name} {input_path} {local_model_path}")
                            download_folder_from_s3_by_tar(input_bucket_name, input_path, local_model_path)
                            # Refresh the ckpt list.
                            sd_models.list_models()
                            logger.info("Check disk usage after download.")
                            os.system("df -h")
                        logger.info("Start creating model.")
                        # local_response = requests.post(url=f'http://0.0.0.0:8080/dreambooth/createModel',
                        #                         params=db_create_model_params)
                        create_model_func_args = copy.deepcopy(db_create_model_params)
                        # ckpt_path = create_model_func_args.pop("new_model_src")
                        # create_model_func_args["ckpt_path"] = ckpt_path
                        local_response = create_model(**create_model_func_args)
                        target_local_model_dir = f'models/dreambooth/{db_create_model_params["new_model_name"]}'
                        logging.info(f"Upload tgt model to s3 {target_local_model_dir} {output_bucket_name} {output_path}")
                        upload_folder_to_s3_by_tar(target_local_model_dir, output_bucket_name, output_path)
                        config_file = os.path.join(target_local_model_dir, "db_config.json")
                        with open(config_file, 'r') as openfile:
                            config_dict = json.load(openfile)
                        message = {
                            "response": local_response,
                            "config_dict": config_dict
                        }
                        response = {
                            "id": job_id,
                            "statusCode": 200,
                            "message": message,
                            "outputLocation": [f'{s3_output_path}/db_create_model_params["new_model_name"]']
                        }
                        return response
                    except Exception as e:
                        response = {
                            "id": job_id,
                            "statusCode": 500,
                            "message": traceback.format_exc(),
                        }
                        logger.error(traceback.format_exc())
                        return response
                    finally:
                        # Clean up
                        logger.info("Delete src model.")
                        delete_src_command = f"rm -rf models/Stable-diffusion/{db_create_model_params['ckpt_path']}"
                        logger.info(delete_src_command)
                        os.system(delete_src_command)
                        logging.info("Delete tgt model.")
                        delete_tgt_command = f"rm -rf models/dreambooth/{db_create_model_params['new_model_name']}"
                        logger.info(delete_tgt_command)
                        os.system(delete_tgt_command)
                        logging.info("Check disk usage after request.")
                        os.system("df -h")
                elif req.task == 'merge-checkpoint':
                    try:
                        output_model_position = merge_model_on_cloud(req)
                        response = {
                            "statusCode": 200,
                            "message": output_model_position,
                        }
                        return response
                    except Exception as e:
                        traceback.print_exc()
                else:
                    raise NotImplementedError
            except Exception as e:
                traceback.print_exc()
            finally:
                thread_deque.popleft()
                condition.notify()

    @app.get("/ping")
    def ping():
        return {'status': 'Healthy'}

import hashlib
def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def get_file_md5_dict(path):
    file_dict = {}
    for root, dirs, files in os.walk(path):
        for file in files:
            file_dict[file] = md5(os.path.join(root, file))
    return file_dict

def move_model_to_tmp(_, app: FastAPI):
    # os.system("rm -rf models")
    # Create model dir
    # logger.info("Create model dir")
    # os.system("mkdir models")
    # Move model dir to /tmp
    logging.info("Copy model dir to tmp")
    model_tmp_dir = f"models_{time.time()}"
    os.system(f"cp -rL models /tmp/{model_tmp_dir}")
    src_file_dict = get_file_md5_dict("models")
    tgt_file_dict = get_file_md5_dict(f"/tmp/{model_tmp_dir}")
    is_complete = True
    for file in src_file_dict:
        logging.info(f"Src file {file} md5 {src_file_dict[file]}")
        if file not in tgt_file_dict:
            is_complete = False
            break
        if src_file_dict[file] != tgt_file_dict[file]:
            is_complete = False
            break
    if is_complete:
        os.system(f"rm -rf models")
        # Delete tmp model dir
        # logger.info("Delete tmp model dir")
        # os.system("rm -rf /tmp/models")
        # Link model dir
        logging.info("Link model dir")
        os.system(f"ln -s /tmp/{model_tmp_dir} models")
    else:
        logging.info("Failed to copy model dir, use the original dir")
    logging.info("Check disk usage on app started")
    os.system("df -h")

try:
    import modules.script_callbacks as script_callbacks

    script_callbacks.on_app_started(sagemaker_api)
    on_docker = os.environ.get('ON_DOCKER', "false")
    if on_docker == "true":
        from modules import shared
        shared.opts.data.update(control_net_max_models_num=10)
        script_callbacks.on_app_started(move_model_to_tmp)
    logger.debug("SD-Webui API layer loaded")
except Exception as e:
    logger.error(e)
    logger.debug("Unable to import script callbacks.")
    pass
