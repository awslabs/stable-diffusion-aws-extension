import base64
import io
import os
import time
import datetime
import uvicorn
from threading import Lock
from fastapi import APIRouter, Depends, FastAPI, Request, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import threading
import json
from secrets import compare_digest
import traceback
import sys
import copy
from modules.api.mme_utils import decode_base64_to_image, encode_pil_to_base64
from modules import shared, scripts, pipeline, errors, sd_models # , sd_samplers
from modules.api.mme_utils import checkspace_and_update_models, payload_filter#, download_model, models_path
from modules.api.utils import read_from_s3, get_bucket_name_from_s3_path, get_path_from_s3_path, download_folder_from_s3_by_tar, upload_folder_to_s3_by_tar
from contextlib import closing
from modules.api import models
from modules.api.lcm_processing import lcm_lora_pipeline, lcm_pipeline

import logging
from dreambooth.sd_to_diff import extract_checkpoint
from diffusers import AutoPipelineForText2Image
import torch

if os.environ.get("DEBUG_API", False):
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

def api_middleware(app: FastAPI):
    rich_available = False
    try:
        if os.environ.get('WEBUI_RICH_EXCEPTIONS', None) is not None:
            import anyio  # importing just so it can be placed on silent list
            import starlette  # importing just so it can be placed on silent list
            from rich.console import Console
            console = Console()
            rich_available = True
    except Exception:
        pass

    @app.middleware("http")
    async def log_and_time(req: Request, call_next):
        ts = time.time()
        res: Response = await call_next(req)
        duration = str(round(time.time() - ts, 4))
        res.headers["X-Process-Time"] = duration
        endpoint = req.scope.get('path', 'err')
        if shared.cmd_opts.api_log and endpoint.startswith('/sdapi'):
            print('API {t} {code} {prot}/{ver} {method} {endpoint} {cli} {duration}'.format(
                t=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                code=res.status_code,
                ver=req.scope.get('http_version', '0.0'),
                cli=req.scope.get('client', ('0:0.0.0', 0))[0],
                prot=req.scope.get('scheme', 'err'),
                method=req.scope.get('method', 'err'),
                endpoint=endpoint,
                duration=duration,
            ))
        return res

    def handle_exception(request: Request, e: Exception):
        err = {
            "error": type(e).__name__,
            "detail": vars(e).get('detail', ''),
            "body": vars(e).get('body', ''),
            "errors": str(e),
        }
        if not isinstance(e, HTTPException):  # do not print backtrace on known httpexceptions
            message = f"API error: {request.method}: {request.url} {err}"
            if rich_available:
                print(message)
                console.print_exception(show_locals=True, max_frames=2, extra_lines=1, suppress=[anyio, starlette], word_wrap=False, width=min([console.width, 200]))
            else:
                errors.report(message, exc_info=True)
        return JSONResponse(status_code=vars(e).get('status_code', 500), content=jsonable_encoder(err))

    @app.middleware("http")
    async def exception_handling(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            return handle_exception(request, e)

    @app.exception_handler(Exception)
    async def fastapi_exception_handler(request: Request, e: Exception):
        return handle_exception(request, e)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, e: HTTPException):
        return handle_exception(request, e)

def script_name_to_index(name, scripts):
    try:
        return [script.title().lower() for script in scripts].index(name.lower())
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Script '{name}' not found") from e


class Api:
    def __init__(self, app: FastAPI, queue_lock: Lock):

        self.router = APIRouter()
        self.app = app
        self.queue_lock = queue_lock
        # # TODO: do we need api_middleware? Xiujuan
        api_middleware(self.app)
        self.add_api_route("/invocations", self.invocations, methods=["POST"], response_model=[])
        self.add_api_route("/ping", self.ping, methods=["GET"], response_model=models.PingResponse)

        # if shared.cmd_opts.api_server_stop:
        #     self.add_api_route("/sdapi/v1/server-kill", self.kill_webui, methods=["POST"])
        #     self.add_api_route("/sdapi/v1/server-restart", self.restart_webui, methods=["POST"])
        #     self.add_api_route("/sdapi/v1/server-stop", self.stop_webui, methods=["POST"])

        self.default_script_arg_txt2img = []
        self.default_script_arg_img2img = []

    def add_api_route(self, path: str, endpoint, **kwargs):
        # TODO: do we need api_auth? Xiujuan
        # if shared.cmd_opts.api_auth:
        #     return self.app.add_api_route(path, endpoint, dependencies=[Depends(self.auth)], **kwargs)
        return self.app.add_api_route(path, endpoint, **kwargs)

    # def auth(self, credentials: HTTPBasicCredentials = Depends(HTTPBasic())):
    #     if credentials.username in self.credentials:
    #         if compare_digest(credentials.password, self.credentials[credentials.username]):
    #             return True

    #     raise HTTPException(status_code=401, detail="Incorrect username or password", headers={"WWW-Authenticate": "Basic"})

    def get_script(self, script_name, script_runner):
        if script_name is None or script_name == "":
            return None, None

        script_idx = script_name_to_index(script_name, script_runner.scripts)
        return script_runner.scripts[script_idx]

    def init_script_args(self, request, script_runner):
        script_args = {}

        # Now check for always on scripts
        if request.alwayson_scripts:
            for alwayson_script_name in request.alwayson_scripts.keys():
                alwayson_script = self.get_script(alwayson_script_name, script_runner)
                if alwayson_script is None:
                    raise HTTPException(status_code=422, detail=f"always on script {alwayson_script_name} not found")
                # Selectable script in always on script param check
                if alwayson_script.alwayson is False:
                    raise HTTPException(status_code=422, detail="Cannot have a selectable script in the always on scripts params")
                # always on script with no arg should always run so you don't really need to add them to the requests
                if "args" in request.alwayson_scripts[alwayson_script_name]:
                    # min between arg length in scriptrunner and arg length in the request
                    filename = alwayson_script.filename
                    script_args[filename] = request.alwayson_scripts[alwayson_script_name]["args"]
                    # for idx in range(0, min((alwayson_script.args_to - alwayson_script.args_from), len(request.alwayson_scripts[alwayson_script_name]["args"]))):
                    #     script_args[alwayson_script.args_from + idx] = request.alwayson_scripts[alwayson_script_name]["args"][idx]
        return script_args
    
    def wuerstchen_pipeline(self, payload):
        txt2imgreq = models.StableDiffusionTxt2ImgProcessingAPI(**payload)
        
        populate = txt2imgreq.copy(update={  # Override __init__ params
            "sampler_name": (txt2imgreq.sampler_name or txt2imgreq.sampler_index),
            "do_not_save_samples": not txt2imgreq.save_images,
            "do_not_save_grid": not txt2imgreq.save_images,
        })
        if populate.sampler_name:
            populate.sampler_index = None  # prevent a warning later on
        args = vars(populate)
        args.pop('script_name', None)
        args.pop('script_args', None) # will refeed them to the pipeline directly after initializing them
        args.pop('alwayson_scripts', None)

        send_images = args.pop('send_images', True)
        args.pop('save_images', None)
        if shared.sd_pipeline.pipeline_name != 'wuerstchen':
            shared.sd_pipeline =  AutoPipelineForText2Image.from_pretrained("warp-diffusion/wuerstchen", torch_dtype=torch.float16).to('cuda')
            shared.sd_pipeline.pipeline_name = 'wuerstchen'
            shared.opts.data["sd_model_checkpoint_path"] = 'wuerstchen'
        output = shared.sd_pipeline(
            prompt=args['prompt'],
            negative_prompt=args['negative_prompt'],
            height=args['height'],
            width=args['width'],
            prior_guidance_scale=args['cfg_scale'],
            decoder_guidance_scale=0.0,
            ).images
        
        b64images = list(map(encode_pil_to_base64, output)) if send_images else []
        return models.TextToImageResponse(images=b64images, parameters=vars(txt2imgreq)) 
    
    def txt2img_pipeline(self, payload):
        txt2imgreq = models.StableDiffusionTxt2ImgProcessingAPI(**payload)
        script_runner = scripts.scripts_txt2img
        if not script_runner.scripts:
            script_runner.initialize_scripts(False)
        
        populate = txt2imgreq.copy(update={  # Override __init__ params
            "sampler_name": (txt2imgreq.sampler_name or txt2imgreq.sampler_index),
            "do_not_save_samples": not txt2imgreq.save_images,
            "do_not_save_grid": not txt2imgreq.save_images,
        })
        if populate.sampler_name:
            populate.sampler_index = None  # prevent a warning later on
        args = vars(populate)
        args.pop('script_name', None)
        args.pop('script_args', None) # will refeed them to the pipeline directly after initializing them
        args.pop('alwayson_scripts', None)

        if 'refiner' in txt2imgreq.alwayson_scripts.keys():
            refiner_args = txt2imgreq.alwayson_scripts['refiner']['args']
            args['use_refiner'] = refiner_args[0]
            args['refiner_checkpoint'] = None
            args['refiner_switch_at'] = None
            if args["use_refiner"]:
                args["refiner_checkpoint"] = refiner_args[1]
                args["refiner_switch_at"] = refiner_args[2]
            del txt2imgreq.alwayson_scripts['refiner']

        script_args = self.init_script_args(txt2imgreq, script_runner)


        send_images = args.pop('send_images', True)
        args.pop('save_images', None)
        with closing(pipeline.StableDiffusionPipelineTxt2Img(sd_model=None, **args)) as p:
            p.scripts = script_runner
            p.script_args = script_args
            processed = pipeline.process_images(p)
            b64images = list(map(encode_pil_to_base64, processed.images)) if send_images else []
            return models.TextToImageResponse(images=b64images, parameters=vars(txt2imgreq), info=processed.js())
    
    def img2img_pipeline(self, payload):
        img2imgreq = models.StableDiffusionImg2ImgProcessingAPI(**payload)
        init_images = img2imgreq.init_images
        if init_images is None:
            raise HTTPException(status_code=404, detail="Init image not found")

        mask = img2imgreq.mask
        if mask:
            mask = decode_base64_to_image(mask)

        script_runner = scripts.scripts_txt2img
        if not script_runner.scripts:
            script_runner.initialize_scripts(True)

        populate = img2imgreq.copy(update={  # Override __init__ params
            "sampler_name": (img2imgreq.sampler_name or img2imgreq.sampler_index),
            "do_not_save_samples": not img2imgreq.save_images,
            "do_not_save_grid": not img2imgreq.save_images,
            "mask": mask,
        })
        if populate.sampler_name:
            populate.sampler_index = None  # prevent a warning later on
        args = vars(populate)
        args.pop('script_name', None)
        args.pop('script_args', None) # will refeed them to the pipeline directly after initializing them
        args.pop('alwayson_scripts', None)
        send_images = args.pop('send_images', True)
        args.pop('save_images', None)

        if 'refiner' in img2imgreq.alwayson_scripts.keys():
            refiner_args = img2imgreq.alwayson_scripts['refiner']['args']
            args['use_refiner'] = refiner_args[0]
            args['refiner_checkpoint'] = None
            args['refiner_switch_at'] = None
            if args["use_refiner"]:
                args["refiner_checkpoint"] = refiner_args[1]
                args["refiner_switch_at"] = refiner_args[2]
            del img2imgreq.alwayson_scripts['refiner']

        script_args = self.init_script_args(img2imgreq, script_runner)
        
        with closing(pipeline.StableDiffusionPipelineImg2Img(sd_model=None, **args)) as p:
            p.init_images = [decode_base64_to_image(x) for x in init_images]
            p.scripts = script_runner
            p.script_args = script_args
            processed = pipeline.process_images(p)
            b64images = list(map(encode_pil_to_base64, processed.images)) if send_images else []
            return models.ImageToImageResponse(images=b64images, parameters=vars(img2imgreq), info=processed.js())

    def invocations(self, req: models.InvocationsRequest):
        """
        @return:
        """
        logger.info('-------invocation------')
        logger.info("Loading Sagemaker API Endpoints.")

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

        start_time = time.time()
        print(f'current version: dev')
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

        payload = payload_filter(payload)
        if 'pipeline_name' in payload:
            req.task = payload['pipeline_name']

        if req.task != 'lcm_lora_pipeline' and 'lcm_lora' in shared.sd_pipeline.pipeline_name:
            shared.sd_pipeline.unload_lora_weights()
        
        logger.info('!!!!!!! payload processing take', time.time()-start_time)
        
        try:
            if req.task == 'txt2img':
                with self.queue_lock:
                    checkspace_and_update_models(req.models)
                    response = self.txt2img_pipeline(payload)
                    logger.info(
                        f"{threading.current_thread().ident}_{threading.current_thread().name}_______ txt2img end !!!!!!!! {len(response.json())}")
                    return response
            elif req.task == 'img2img':
                with self.queue_lock:
                    checkspace_and_update_models(req.models)
                    response = self.img2img_pipeline(payload)
                    logger.info(
                        f"{threading.current_thread().ident}_{threading.current_thread().name}_______ img2img end !!!!!!!! {len(response.json())}")
                    return response
            elif req.task == 'wuerstchen':
                with self.queue_lock:
                    response = self.wuerstchen_pipeline(payload)
                    logger.info(
                        f"{threading.current_thread().ident}_{threading.current_thread().name}_______ img2img end !!!!!!!! {len(response.json())}")
                    return response
            elif req.task == 'lcm_pipeline':
                with self.queue_lock:
                    response = lcm_pipeline(payload, req.models)
                    logger.info(
                        f"{threading.current_thread().ident}_{threading.current_thread().name}_______ img2img end !!!!!!!! {len(response.json())}")
                    return response
            elif req.task == 'lcm_lora_pipeline':
                with self.queue_lock:
                    sd_model_update_dict={}
                    sd_model_update_dict['space_free_size'] = req.models['space_free_size']
                    sd_model_update_dict['Stable-diffusion'] = req.models['Stable-diffusion']
                    checkspace_and_update_models(sd_model_update_dict)
                    response = lcm_lora_pipeline(payload, req.models)
                    logger.info(
                        f"{threading.current_thread().ident}_{threading.current_thread().name}_______ img2img end !!!!!!!! {len(response.json())}")
                    return response   
            elif req.task == 'db-create-model':
                # logger.info("db-create-model not implemented!")
                # return 0
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
                        logger.info(
                            f"Download src model from s3 {input_bucket_name} {input_path} {local_model_path}")
                        # download_folder_from_s3_by_tar(input_bucket_name, input_path, local_model_path)
                        # Refresh the ckpt list.
                        sd_models.list_models()
                        logger.info("Check disk usage after download.")
                        os.system("df -h")
                    logger.info("Start creating model.")
                    # local_response = requests.post(url=f'http://0.0.0.0:8080/dreambooth/createModel',
                    #                         params=db_create_model_params)
                    new_model_name = db_create_model_params["new_model_name"]
                    ckpt_path = db_create_model_params["ckpt_path"]
                    extract_ema = db_create_model_params["extract_ema"]
                    train_unfrozen = db_create_model_params["train_unfrozen"]
                    res = 512
                    model_type = "v1"
                    # create_model_func_args = copy.deepcopy(db_create_model_params)
                    # ckpt_path = create_model_func_args.pop("new_model_src")
                    # create_model_func_args["ckpt_path"] = ckpt_path
                    # local_response = create_model(**create_model_func_args)
                    result = extract_checkpoint(
                            new_model_name=new_model_name,
                            checkpoint_file=ckpt_path,
                            extract_ema=extract_ema,
                            train_unfrozen=train_unfrozen,
                            image_size=res,
                            model_type=model_type)
                    target_local_model_dir = f'models/dreambooth/{db_create_model_params["new_model_name"]}'
                    logging.info(
                        f"Upload tgt model to s3 {target_local_model_dir} {output_bucket_name} {output_path}")
                    upload_folder_to_s3_by_tar(target_local_model_dir, output_bucket_name, output_path)
                    config_file = os.path.join(target_local_model_dir, "db_config.json")
                    with open(config_file, 'r') as openfile:
                        config_dict = json.load(openfile)
                    message = {
                        "response": result,
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
            else:
                raise NotImplementedError
        except Exception as e:
            traceback.print_exc()
        
        logger.info('!!!!!!! inference take', time.time()-start_time)

    def ping(self):
        return {'status': 'Healthy'}

    def launch(self, server_name, port):
        self.app.include_router(self.router)
        uvicorn.run(self.app, host=server_name, port=port, timeout_keep_alive=shared.cmd_opts.timeout_keep_alive)

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
        logging.info("Link model dir")
        os.system(f"ln -s /tmp/{model_tmp_dir} models")
    else:
        logging.info("Failed to copy model dir, use the original dir")
    logging.info("Check disk usage on app started")
    os.system("df -h")

try:
    import modules.script_callbacks as script_callbacks

    on_docker = os.environ.get('ON_DOCKER', "false")
    if on_docker == "true":
        from modules import shared
        shared.opts.data.update(control_net_max_models_num=10)
        script_callbacks.on_app_started(move_model_to_tmp)
    logger.debug("Diffusers API layer loaded")
except Exception as e:
    logger.error(e)
    logger.debug("Unable to import script callbacks.")
    pass