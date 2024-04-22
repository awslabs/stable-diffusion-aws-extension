import asyncio
import datetime
import logging
import os
import subprocess
import threading
from multiprocessing import Process
from threading import Lock
import requests
import socket
import uvicorn
from fastapi import APIRouter, FastAPI, Request, HTTPException

import multiprocessing
import queue
import time
import psutil
from enum import Enum

TIMEOUT_KEEP_ALIVE = 30
# COMFY_PORT = 8188
SAGEMAKER_PORT = 8080
LOCALHOST = '0.0.0.0'
PHY_LOCALHOST = '127.0.0.1'

SLEEP_TIME = 30

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

sagemaker_safe_port_range = os.getenv('SAGEMAKER_SAFE_PORT_RANGE')
start_port = int(sagemaker_safe_port_range.split('-')[0])
global available_apps
available_apps=[]

global is_multi_gpu
is_multi_gpu=False


async def send_request(request_obj):
    comfy_app = check_available_app(True)
    if comfy_app is None:
        raise HTTPException(status_code=500, detail=f"COMFY service not available for multi reqs")
    comfy_app.busy = True
    logger.info(f"Invocations start req: {request_obj}, url: {PHY_LOCALHOST}:{comfy_app.port}/execute_proxy")
    response = requests.post(f"http://{PHY_LOCALHOST}:{comfy_app.port}/execute_proxy", json=request_obj)
    comfy_app.busy = False
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code,
                            detail=f"COMFY service returned an error: {response.text}")
    return response.json()


async def invocations(request: Request):
    global is_multi_gpu
    if not is_multi_gpu:
        gpu_nums = get_gpu_count()
        logger.info(f"Number of GPUs: {gpu_nums}")
        req = await request.json()
        logger.info(f"Starting single invocation {req}")
        tasks = [send_request(request_obj) for request_obj in req]
        results = await asyncio.gather(*tasks)
        logger.info(f'Finished invocations {results}')
        return results
    else:
        comfy_app = check_available_app(True)
        if comfy_app is None:
            raise HTTPException(status_code=500,detail=f"COMFY service not available for single")
        req = await request.json()
        logger.info(f"Starting single invocation on {comfy_app.port} {req}")
        result = []
        for request_obj in req:
            logger.info(f"invocations start req:{request_obj}  url:{PHY_LOCALHOST}:{comfy_app.port}/execute_proxy")
            response = requests.post(f"http://{PHY_LOCALHOST}:{comfy_app.port}/execute_proxy", json=request_obj)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code,
                                    detail=f"COMFY service returned an error: {response.text}")
            result.append(response.json())
        return result


def ping():
    init_already = os.environ.get('ALREADY_INIT')
    if init_already and init_already.lower() == 'false':
        raise HTTPException(status_code=500)
    # else:
    #     return {'status': 'Healthy'}
    comfy_app = check_available_app(False)
    if comfy_app is None:
        raise HTTPException(status_code=500)
    logger.info(f"check status start url:{PHY_LOCALHOST}:{comfy_app.port}/queue")
    response = requests.get(f"http://{PHY_LOCALHOST}:{comfy_app.port}/queue")
    if response.status_code != 200:
        raise HTTPException(status_code=500)
    return {'status': 'Healthy'}


class Api:
    def add_api_route(self, path: str, endpoint, **kwargs):
        return self.app.add_api_route(path, endpoint, **kwargs)

    def __init__(self, app: FastAPI, queue_lock: Lock):
        self.router = APIRouter()
        self.app = app
        self.queue_lock = queue_lock
        self.add_api_route("/invocations", invocations, methods=["POST"])
        self.add_api_route("/ping", ping, methods=["GET"], response_model={})

    def launch(self, server_name, port):
        self.app.include_router(self.router)
        uvicorn.run(self.app, host=server_name, port=port, timeout_keep_alive=TIMEOUT_KEEP_ALIVE)


class ComfyApp:
    def __init__(self, host, port, device_id):
        self.host = host
        self.port = port
        self.device_id = device_id
        self.process = None
        self.busy = False

    def start(self):
        cmd = ["python", "main.py", "--listen", self.host, "--port", str(self.port), "--output-directory", f"/home/ubuntu/ComfyUI/output/{self.device_id}/", "--temp-directory",f"/home/ubuntu/ComfyUI/temp/{self.device_id}/","--cuda-device", str(self.device_id)]
        self.process = subprocess.Popen(cmd)
        os.environ['ALREADY_INIT'] = 'true'

    def restart(self):
        logger.info("Comfy app process is going to restart")
        if self.process and self.process.poll() is None:
            os.environ['ALREADY_INIT'] = 'false'
            self.process.terminate()
            self.process.wait()
        self.start()

    def is_port_ready(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', self.port))
            return result == 0


def get_gpu_count():
    try:
        result = subprocess.run(['nvidia-smi', '-L'], capture_output=True, text=True, check=True)
        gpu_count = result.stdout.count('\n')
        return gpu_count
    except subprocess.CalledProcessError as e:
        logger.info("Failed to run nvidia-smi:", e)
        return 0
    except Exception as e:
        logger.info("An error occurred:", e)
        return 0


def start_comfy_servers():
    global is_multi_gpu
    gpu_nums = get_gpu_count()
    if gpu_nums > 1:
        is_multi_gpu = True
    else:
        is_multi_gpu = False
    logger.info(f"is_multi_gpu is {is_multi_gpu}")
    for gpu_num in range(gpu_nums):
        logger.info(f"start comfy server by device_id: {gpu_num}")
        port = start_port + gpu_num
        comfy_app = ComfyApp(host=LOCALHOST, port=port, device_id=gpu_num)
        comfy_app.start()
        global available_apps
        available_apps.append(comfy_app)


def get_available_app(need_check_busy: bool):
    global available_apps
    if available_apps is None:
        return None
    for item in available_apps:
        if need_check_busy:
            if item.is_port_ready() and not item.busy:
                return item
        else:
            if item.is_port_ready():
                return item
    return None


def check_available_app(need_check_busy: bool):
    comfy_app = get_available_app(need_check_busy)
    i = 0
    while comfy_app is None:
        comfy_app = get_available_app(need_check_busy)
        if comfy_app is None:
            asyncio.sleep(1)
            i += 1
            if i >= 3:
                logger.info(f"There is no available comfy_app for {i} attempts.")
                break
    if comfy_app is None:
        logger.info(f"There is no available comfy_app! Ignoring this request")
        return None
    return comfy_app


def check_sync():
    logger.info("start check_sync!")
    while True:
        try:
            comfy_app = check_available_app(False)
            if comfy_app is None:
                raise HTTPException(status_code=500,
                                    detail=f"COMFY service returned an error: no avaliable app")
            logger.info("start check_sync! checking function-------")
            response = requests.post(f"http://{PHY_LOCALHOST}:{comfy_app.port}/sync_instance")
            logger.info(f"sync response:{response.json()} time : {datetime.datetime.now()}")

            logger.info("start check_reboot! checking function-------")
            requests.post(f"http://{PHY_LOCALHOST}:{comfy_app.port}/reboot")
            logger.info(f"reboot response time : {datetime.datetime.now()}")
            time.sleep(SLEEP_TIME)
        except Exception as e:
            logger.info(f"check_and_reboot error:{e}")
            time.sleep(SLEEP_TIME)


if __name__ == "__main__":
    queue_lock = threading.Lock()
    api = Api(app, queue_lock)
    start_comfy_servers()

    # comfy_app = ComfyApp()
    api_process = Process(target=api.launch, args=(LOCALHOST, SAGEMAKER_PORT))

    check_sync_thread = threading.Thread(target=check_sync)

    # comfy_app.start()
    api_process.start()
    check_sync_thread.start()

    api_process.join()


