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

class ProcessState(Enum):
    RUNNING = 'Running'
    INTERRUPTIBLE_SLEEP = 'InterruptibleSleep'
    UNINTERRUPTIBLE_SLEEP = 'UninterruptibleSleep'
    STOPPED = 'Stopped'
    ZOMBIE = 'Zombie'


class Job:
    def __init__(self, job_id, req, serve_app):
        self.job_id = job_id
        self.serve_app = serve_app
        self.req = req
        self.state = ProcessState.RUNNING
        self.result = None
        self.error = None


class Worker(multiprocessing.Process):
    def __init__(self, task_queue, result_queue):
        super().__init__()
        self.task_queue = task_queue
        self.result_queue = result_queue

    def run(self):
        while True:
            try:
                job = self.task_queue.get(timeout=1)
                # Create a new process for the job
                process = multiprocessing.Process(target=self.process_job, args=(job,))
                process.start()
                while True:
                    try:
                        status = psutil.Process(process.pid).status()
                        if status == psutil.STATUS_RUNNING:
                            job.state = ProcessState.RUNNING
                        elif status == psutil.STATUS_SLEEPING:
                            job.state = ProcessState.INTERRUPTIBLE_SLEEP
                        elif status == psutil.STATUS_DISK_SLEEP:
                            job.state = ProcessState.UNINTERRUPTIBLE_SLEEP
                        else:
                            # Handle other states if needed
                            break
                    except psutil.NoSuchProcess:
                        break
                logging.info(job.state)
                # Wait for the process to finish and get the result or error
                process.join()
                if job.error is None:
                    job.result = f"Result for job {job.job_id}"
            except queue.Empty:
                break
            finally:
                self.result_queue.put(job)

    def process_job(self, job):
        try:
            # time.sleep(random.uniform(1, 5))
            comfy_app = job.serve_app
            req = job.req
            if comfy_app is None:
                raise HTTPException(status_code=500,
                                    detail=f"COMFY service returned an error: no avaliable app")
            response = requests.post(f"http://{PHY_LOCALHOST}:{comfy_app.port}/execute_proxy", json=req)
            return response.json()

        except Exception as e:
            job.error = str(e)


class ProcessLifecycleController:
    def __init__(self, num_workers):
        self.num_workers = num_workers
        self.task_queue = multiprocessing.Queue()
        self.result_queue = multiprocessing.Queue()
        self.jobs = {}
        self.workers = []

    def start(self):
        for _ in range(self.num_workers):
            worker = Worker(self.task_queue, self.result_queue)
            worker.start()
            self.workers.append(worker)

    def submit_job(self, req, serve_app):
        job_id = len(self.jobs)
        job = Job(job_id, req, serve_app)
        self.jobs[job_id] = job
        self.task_queue.put(job)
        return job_id

    def get_job_status(self, job_id):
        job = self.jobs.get(job_id)
        if job:
            return job.state
        return None

    def get_job_result(self, job_id):
        job = self.jobs.get(job_id)
        if job and job.state == ProcessState.ZOMBIE and job.result is not None:
            return job.result
        return None

    def get_job_error(self, job_id):
        job = self.jobs.get(job_id)
        if job and job.state == ProcessState.ZOMBIE and job.error is not None:
            return job.error
        return None

    def monitor_jobs(self):
        completed_jobs = []
        while True:
            try:
                job = self.result_queue.get(timeout=1)
                if job.state == ProcessState.ZOMBIE:
                    if job.error is None:
                        completed_jobs.append(job.job_id)
                    else:
                        print(f"Job {job.job_id} failed: {job.error}")
                        if job.job_id in self.jobs:
                            del self.jobs[job.job_id]
            except queue.Empty:
                break

        for job_id in completed_jobs:
            if job_id in self.jobs:
                del self.jobs[job_id]

    def stop(self):
        for worker in self.workers:
            worker.terminate()
        self.workers.clear()


async def invocations(request: Request):
    global is_multi_gpu
    if is_multi_gpu:
        gpu_nums = get_gpu_count()
        controller = ProcessLifecycleController(num_workers=gpu_nums)
        controller.start()
        job_ids = []
        req_list = await request.json()
        result_list = []

        for request_obj in req_list:
            job_id = controller.submit_job(request_obj, get_available_app())
            job_ids.append(job_id)
        # Monitor job status and results
        while job_ids:
            for job_id in job_ids:
                status = controller.get_job_status(job_id)
                print(f"Job {job_id} status: {status}")
                if status == ProcessState.ZOMBIE:
                    result = controller.get_job_result(job_id)
                    if result is not None:
                        result_list.append(result)
                        print(f"Job {job_id} completed. Result: {result}")
                        job_ids.remove(job_id)
                    else:
                        error = controller.get_job_error(job_id)
                        print(f"Job {job_id} failed. Error: {error}")
                        job_ids.remove(job_id)
                elif status is None:
                    print(f"Job {job_id} status is None")
                    job_ids.remove(job_id)
            controller.monitor_jobs()
            # time.sleep(1)
        controller.stop()
        return result_list
    else:
        comfy_app = get_available_app()
        req = await request.json()
        result = []
        for request_obj in req:
            logger.info(f"invocations start req:{req}  url:{PHY_LOCALHOST}:{comfy_app.port}/invocations")
            response = requests.post(f"http://{PHY_LOCALHOST}:{comfy_app.port}/invocations", json=request_obj)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code,
                                    detail=f"COMFY service returned an error: {response.text}")
            result.append(response.json())
        return result


def ping():
    init_already = os.environ.get('ALREADY_INIT')
    if init_already and init_already.lower() == 'false':
        raise HTTPException(status_code=500)
    else:
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
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.process = None
        self.busy = False

    def start(self):
        # cmd = "python main.py  --listen {} --port {}".format(self.host, self.port)
        # self.process = Process(target=os.system, args=(cmd,))
        # self.process.start()
        cmd = ["python", "main.py", "--listen", self.host, "--port", str(self.port)]
        self.process = subprocess.Popen(cmd)
        os.environ['ALREADY_INIT'] = 'true'

    def restart(self):
        # if self.process and self.process.is_alive():
        #     self.process.terminate()
        #     self.start()
        # else:
        #     logger.info("Comfy app process is not running.")
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

    async def execute_entry(self, req):
        self.busy = True
        req['out_path'] = self.port
        logger.info(f"invocations start req:{req}  url:{PHY_LOCALHOST}:{self.port}/execute_proxy")
        response = requests.post(f"http://{PHY_LOCALHOST}:{self.port}/execute_proxy", json=req)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code,
                                detail=f"COMFY service returned an error: {response.text}")
        return response.json()

    def check_status(self):
        logger.info(f"check status start   url:{PHY_LOCALHOST}:{self.port}/queue")
        response = requests.get(f"http://{PHY_LOCALHOST}:{self.port}/queue")
        if response.status_code != 200:
            return False
        return True


def get_gpu_count():
    try:
        result = subprocess.run(['nvidia-smi', '-L'], capture_output=True, text=True, check=True)
        gpu_count = result.stdout.count('\n')
        return gpu_count
    except subprocess.CalledProcessError as e:
        print("Failed to run nvidia-smi:", e)
        return 0
    except Exception as e:
        print("An error occurred:", e)
        return 0


def start_comfy_servers():
    gpu_nums = get_gpu_count()
    global is_multi_gpu
    if gpu_nums > 1:
        is_multi_gpu = True
    else:
        is_multi_gpu = False
    for gpu_num in range(gpu_nums):
        logger.info(f"start comfy server by device_id: {gpu_num}")
        port = start_port + gpu_num
        comfy_app = ComfyApp(host=LOCALHOST, port=port)
        comfy_app.start()
        global available_apps
        if available_apps is None:
            available_apps = []
        available_apps.append(comfy_app)


def get_available_app():
    global available_apps
    if available_apps is None:
        return None
    for item in available_apps:
        if item.is_port_ready() and not item.busy:
            return item


def check_sync():
    logger.info("start check_sync!")
    while True:
        try:
            comfy_app = get_available_app()
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


