import asyncio
import logging
import os
import subprocess
import threading
from multiprocessing import Process
from threading import Lock
import datetime

import boto3
import httpx
import requests
import socket
import uvicorn
from fastapi import APIRouter, FastAPI, Request, HTTPException

import time

TIMEOUT_KEEP_ALIVE = 30
SAGEMAKER_PORT = 8080
LOCALHOST = '0.0.0.0'
PHY_LOCALHOST = '127.0.0.1'

SLEEP_TIME = 60
TIME_OUT_TIME = 600

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

sagemaker_safe_port_range = os.getenv('SAGEMAKER_SAFE_PORT_RANGE')
start_port = int(sagemaker_safe_port_range.split('-')[0])
available_apps = []
is_multi_gpu = False
cloudwatch = boto3.client('cloudwatch')

endpoint_name = os.getenv('ENDPOINT_NAME')
endpoint_instance_id = os.getenv('ENDPOINT_INSTANCE_ID', 'default')


async def send_request(request_obj, comfy_app, need_async):
    try:
        record_metric(comfy_app)
        logger.info(request_obj)
        logger.info(f"Starting on {comfy_app.port} {need_async} {request_obj}")
        comfy_app.busy = True
        request_obj['port'] = comfy_app.port
        request_obj['out_path'] = comfy_app.device_id
        logger.info(f"Invocations start req: {request_obj}, url: {PHY_LOCALHOST}:{comfy_app.port}/execute_proxy")
        if need_async:
            async with httpx.AsyncClient(timeout=TIME_OUT_TIME) as client:
                response = await client.post(f"http://{PHY_LOCALHOST}:{comfy_app.port}/execute_proxy", json=request_obj)
        else:
            response = requests.post(f"http://{PHY_LOCALHOST}:{comfy_app.port}/execute_proxy", json=request_obj)
        comfy_app.busy = False
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code,
                                detail=f"COMFY service returned an error: {response.text}")
        return wrap_response(response, comfy_app)
    except Exception as e:
        logger.error(f"send_request error {e}")
        raise HTTPException(status_code=500, detail=f"COMFY service not available for multi reqs {e}")
    finally:
        comfy_app.busy = False


async def invocations(request: Request):
    global is_multi_gpu
    try:
        if is_multi_gpu:
            gpu_nums = get_gpu_count()
            logger.info(f"Number of GPUs: {gpu_nums}")
            req = await request.json()
            logger.info(f"Starting multi invocation {req}")

            tasks = []
            for request_obj in req:
                comfy_app = check_available_app(True)
                if comfy_app is None:
                    raise HTTPException(status_code=500, detail=f"COMFY service not available for multi reqs")
                tasks.append(send_request(request_obj, comfy_app, True))
            logger.info("all tasks completed send, waiting result")
            results = await asyncio.gather(*tasks)
            logger.info(f'Finished invocations {results}')
            return results
        else:
            req = await request.json()
            result = []
            logger.info(f"Starting single invocation request is: {req}")
            for request_obj in req:
                comfy_app = check_available_app(True)
                if comfy_app is None:
                    raise HTTPException(status_code=500, detail=f"COMFY service not available for single reqs")
                response = await send_request(request_obj, comfy_app, False)
                result.append(response)
            logger.info(f"Finished invocations result: {result}")
            return result
    except Exception as e:
        logger.error(f"invocations error of {e}")
        return []


def ping():
    init_already = os.environ.get('ALREADY_INIT')
    if init_already and init_already.lower() == 'false':
        raise HTTPException(status_code=500)

    comfy_app = check_available_app(False)
    if comfy_app is None:
        raise HTTPException(status_code=500)
    logger.debug(f"check status start url:{PHY_LOCALHOST}:{comfy_app.port}/queue")
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
        cmd = ["python", "main.py", "--listen", self.host, "--port", str(self.port), "--output-directory",
               f"/home/ubuntu/ComfyUI/output/{self.device_id}/", "--temp-directory",
               f"/home/ubuntu/ComfyUI/temp/{self.device_id}/", "--cuda-device", str(self.device_id)]
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


def wrap_response(response, comfy_app: ComfyApp):
    data = response.json()
    data['endpoint_instance_id'] = os.getenv('ENDPOINT_INSTANCE_ID')
    data['device_id'] = comfy_app.device_id
    return data


def record_metric(comfy_app: ComfyApp):
    response = cloudwatch.put_metric_data(
        Namespace='ESD',
        MetricData=[
            {
                'MetricName': 'InferenceCount',
                'Dimensions': [
                    {
                        'Name': 'Endpoint',
                        'Value': endpoint_name
                    },
                    {
                        'Name': 'Instance',
                        'Value': endpoint_instance_id
                    },
                ],
                'Timestamp': datetime.datetime.utcnow(),
                'Value': 1,
                'Unit': 'Count'
            },
        ]
    )
    logger.info(f"record_metric response: {response}")

    response = cloudwatch.put_metric_data(
        Namespace='ESD',
        MetricData=[
            {
                'MetricName': 'InferenceCount',
                'Dimensions': [
                    {
                        'Name': 'Endpoint',
                        'Value': endpoint_name
                    },
                    {
                        'Name': 'Instance',
                        'Value': endpoint_instance_id
                    },
                    {
                        'Name': 'InstanceGPU',
                        'Value': str(comfy_app.device_id)
                    }
                ],
                'Timestamp': datetime.datetime.utcnow(),
                'Value': 1,
                'Unit': 'Count'
            },
        ]
    )
    logger.info(f"record_metric response: {response}")


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
        available_apps.append(comfy_app)


def get_available_app(need_check_busy: bool):
    global available_apps
    if available_apps is None:
        return None
    for item in available_apps:
        logger.debug(f"get available apps {item.device_id} {item.busy}")
        if need_check_busy:
            if item.is_port_ready() and not item.busy:
                item.busy = True
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
            time.sleep(1)
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

            global available_apps
            for item in available_apps:
                if item and item.port and not item.busy:
                    logger.info(f"start check_reboot! {item.port}")
                    requests.post(f"http://{PHY_LOCALHOST}:{item.port}/reboot")
                    logger.debug(f"reboot response time : {datetime.datetime.now()}")
                else:
                    logger.info(f"not start check_reboot! {item}")
            time.sleep(SLEEP_TIME)
        except Exception as e:
            logger.info(f"check_and_reboot error:{e}")
            time.sleep(SLEEP_TIME)


if __name__ == "__main__":
    queue_lock = threading.Lock()
    api = Api(app, queue_lock)
    start_comfy_servers()

    api_process = Process(target=api.launch, args=(LOCALHOST, SAGEMAKER_PORT))
    check_sync_thread = threading.Thread(target=check_sync)

    api_process.start()
    check_sync_thread.start()

    api_process.join()
