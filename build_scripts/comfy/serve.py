import asyncio
import datetime
import logging
import os
import socket
import subprocess
import sys
import threading
import time
from multiprocessing import Process
from threading import Lock

import boto3
import httpx
import requests
import uvicorn
from fastapi import APIRouter, FastAPI, Request, HTTPException

TIMEOUT_KEEP_ALIVE = 30
SAGEMAKER_PORT = 8080
LOCALHOST = '0.0.0.0'
PHY_LOCALHOST = '127.0.0.1'

SLEEP_TIME = 60
TIME_OUT_TIME = 86400
MAX_KEEPALIVE_CONNECTIONS = 100
MAX_CONNECTIONS = 1500

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

ddb_client = boto3.resource('dynamodb')
inference_table = ddb_client.Table('ComfyExecuteTable')


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
        self.cwd = '/home/ubuntu/ComfyUI'
        self.name = f"{endpoint_instance_id}-gpus-{device_id}"
        self.stdout_thread = None
        self.stderr_thread = None

    def _handle_output(self, pipe, _):
        with pipe:
            for line in iter(pipe.readline, ''):
                if line.strip():
                    file = f"/tmp/gpu{self.device_id}"
                    if os.path.exists(file):
                        with open(file, "r") as file:
                            cur_prompt_id = file.read().strip()
                            if cur_prompt_id:
                                sys.stdout.write(f"{self.name}-prompt-{cur_prompt_id}: {line}")
                            else:
                                sys.stdout.write(f"{self.name}: {line}")
                    else:
                        sys.stdout.write(f"{self.name}: {line}")

    def start(self):
        cmd = ["python", "main.py", "--listen", self.host, "--port", str(self.port), "--output-directory",
               f"/home/ubuntu/ComfyUI/output/{self.device_id}/", "--temp-directory",
               f"/home/ubuntu/ComfyUI/temp/{self.device_id}/", "--cuda-device", str(self.device_id)]
        self.process = subprocess.Popen(
            cmd,
            cwd=self.cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        os.environ['ALREADY_INIT'] = 'true'

        self.stdout_thread = threading.Thread(target=self._handle_output, args=(self.process.stdout, "STDOUT"))
        self.stderr_thread = threading.Thread(target=self._handle_output, args=(self.process.stderr, "STDERR"))

        self.stdout_thread.start()
        self.stderr_thread.start()

    def restart(self):
        logger.info("Comfy app process is going to restart")
        if self.process and self.process.poll() is None:
            os.environ['ALREADY_INIT'] = 'false'
            self.process.terminate()
            self.process.wait()
            self.stdout_thread.join()
            self.stderr_thread.join()
        self.start()

    def is_port_ready(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', self.port))
            return result == 0

    def set_prompt(self, request_obj=None):
        if request_obj and 'prompt_id' in request_obj:
            prompt_id = request_obj['prompt_id']
        else:
            prompt_id = ""

        logger.info(f"set_prompt '{prompt_id}' on device {self.device_id}")
        with open(f"/tmp/gpu{self.device_id}", "w") as f:
            f.write(str(prompt_id))


def update_execute_job_table(prompt_id, key, value):
    logger.info(f"Update job with prompt_id: {prompt_id}, key: {key}, value: {value}")
    try:
        inference_table.update_item(
            Key={
                "prompt_id": prompt_id,
            },
            UpdateExpression=f"set #k = :r",
            ExpressionAttributeNames={'#k': key},
            ExpressionAttributeValues={':r': value},
            ConditionExpression="attribute_exists(prompt_id)",
            ReturnValues="UPDATED_NEW"
        )
    except Exception as e:
        logger.error(f"Update execute job table error: {e}")
        raise e


async def send_request(request_obj, comfy_app: ComfyApp, need_async: bool):
    try:
        record_metric(comfy_app)
        logger.info(f"Starting on {comfy_app.port} {need_async} {request_obj}")

        comfy_app.busy = True
        comfy_app.set_prompt(request_obj)

        request_obj['port'] = comfy_app.port
        request_obj['out_path'] = comfy_app.device_id

        start_time = datetime.datetime.now().isoformat()
        update_execute_job_table(prompt_id=request_obj['prompt_id'], key="start_time", value=start_time)

        logger.info(f"Invocations start req: {request_obj}, url: {PHY_LOCALHOST}:{comfy_app.port}/execute_proxy")
        # if need_async:
        #     async with httpx.AsyncClient(timeout=TIME_OUT_TIME,
        #                                  limits=httpx.Limits(max_keepalive_connections=MAX_KEEPALIVE_CONNECTIONS,
        #                                                      max_connections=MAX_CONNECTIONS)) as client:
        #         response = await client.post(f"http://{PHY_LOCALHOST}:{comfy_app.port}/execute_proxy", json=request_obj)
        # else:
        #     response = requests.post(f"http://{PHY_LOCALHOST}:{comfy_app.port}/execute_proxy", json=request_obj)
        async with httpx.AsyncClient(timeout=TIME_OUT_TIME,
                                     limits=httpx.Limits(max_keepalive_connections=MAX_KEEPALIVE_CONNECTIONS,
                                                         max_connections=MAX_CONNECTIONS)) as client:
            response = await client.post(f"http://{PHY_LOCALHOST}:{comfy_app.port}/execute_proxy", json=request_obj)

        comfy_app.busy = False
        comfy_app.set_prompt()

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code,
                                detail=f"COMFY service returned an error: {response.text}")
        return wrap_response(start_time, response, comfy_app)
    except Exception as e:
        logger.error(f"send_request error {e}")
        raise HTTPException(status_code=500, detail=f"COMFY service not available for internal multi reqs {e}")
    finally:
        comfy_app.busy = False
        comfy_app.set_prompt()


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
                max_retries = TIME_OUT_TIME
                while comfy_app is None:
                    if max_retries > 0:
                        max_retries = max_retries - 60
                        time.sleep(60)
                        comfy_app = check_available_app(True)
                    else:
                        raise HTTPException(status_code=500, detail=f"COMFY service not available for multi reqs")
                # if comfy_app is None:
                #     raise HTTPException(status_code=500, detail=f"COMFY service not available for multi reqs")
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


def wrap_response(start_time, response, comfy_app: ComfyApp):
    data = response.json()
    data['start_time'] = start_time
    data['endpoint_name'] = os.getenv('ENDPOINT_NAME')
    data['endpoint_instance_id'] = os.getenv('ENDPOINT_INSTANCE_ID')
    data['device_id'] = comfy_app.device_id
    return data


def record_metric(comfy_app: ComfyApp):
    response = cloudwatch.put_metric_data(
        Namespace='ESD',
        MetricData=[
            {
                'MetricName': 'InferenceTotal',
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
            {
                'MetricName': 'InferenceTotal',
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
                        'Value': f"GPU{comfy_app.device_id}"
                    }
                ],
                'Timestamp': datetime.datetime.utcnow(),
                'Value': 1,
                'Unit': 'Count'
            },
            {
                'MetricName': 'InferenceEndpointReceived',
                'Dimensions': [
                    {
                        'Name': 'Service',
                        'Value': 'Comfy'
                    },
                ],
                'Timestamp': datetime.datetime.utcnow(),
                'Value': 1,
                'Unit': 'Count'
            },
            {
                'MetricName': 'InferenceEndpointReceived',
                'Dimensions': [
                    {
                        'Name': 'Endpoint',
                        'Value': endpoint_name
                    },
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
    logger.debug("start check_sync!")
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


def get_gpu_utilization():
    try:
        output = subprocess.check_output(['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'])
        gpu_utilization = [int(util.strip()) for util in output.decode('utf-8').split('\n') if util.strip()]
        return gpu_utilization
    except subprocess.CalledProcessError:
        return None


def get_gpu_memory_utilization():
    try:
        output = subprocess.check_output(
            ['nvidia-smi', '--query-gpu=utilization.memory', '--format=csv,noheader,nounits'])
        gpu_memory_utilization = [int(utilization.strip()) for utilization in output.decode('utf-8').split('\n') if
                                  utilization.strip()]
        return gpu_memory_utilization
    except subprocess.CalledProcessError:
        return None


def gpu_metrics():
    data = []
    utilization = get_gpu_utilization()
    if utilization is not None:
        for device_id, util in enumerate(utilization):
            data.append({
                'MetricName': 'GPUUtilization',
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
                        'Value': f"GPU{device_id}"
                    }
                ],
                'Timestamp': datetime.datetime.utcnow(),
                'Value': util,
                'Unit': 'Percent'
            })

    memory_utilization = get_gpu_memory_utilization()
    if memory_utilization is not None:
        for device_id, utilization in enumerate(memory_utilization):
            data.append({
                'MetricName': 'GPUMemoryUtilization',
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
                        'Value': f"GPU{device_id}"
                    }
                ],
                'Timestamp': datetime.datetime.utcnow(),
                'Value': utilization,
                'Unit': 'Percent'
            })

    response = cloudwatch.put_metric_data(
        Namespace='ESD',
        MetricData=data
    )
    logger.debug(f"gpu_metrics response: {response}")


def monitor_gpu_info(interval=10):
    while True:
        time.sleep(interval)
        try:
            gpu_metrics()
        except Exception as e:
            logger.error(f"Error in monitoring GPU info: {e}")


if __name__ == "__main__":
    queue_lock = threading.Lock()
    api = Api(app, queue_lock)
    start_comfy_servers()

    api_process = Process(target=api.launch, args=(LOCALHOST, SAGEMAKER_PORT))
    check_sync_thread = threading.Thread(target=check_sync)

    api_process.start()
    check_sync_thread.start()
    gpu_metrics_thread = threading.Thread(target=monitor_gpu_info, args=(10,))
    gpu_metrics_thread.start()

    api_process.join()
