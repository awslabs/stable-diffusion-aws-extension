import asyncio
import datetime
import json
import logging
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from typing import List

import aiohttp
import boto3
import requests
import uvicorn
from fastapi import FastAPI, Request
from fastapi import Response, status

sagemaker = boto3.client('sagemaker')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Controller")
logger.setLevel(logging.INFO)
app = FastAPI()
SLEEP_TIME = 30
service_type = os.getenv('SERVICE_TYPE', 'sd')
endpoint_name = os.getenv('ENDPOINT_NAME')
should_exit = 0


class App:
    def __init__(self, device_id):
        self.host = "127.0.0.1"
        self.device_id = device_id
        self.port = 24000 + device_id
        self.name = f"{service_type}-gpu{device_id}"
        self.process = None
        self.busy = False
        self.stdout_thread = None
        self.stderr_thread = None
        self.cmd = None
        self.cwd = None

    def start(self):
        self.cwd = '/home/ubuntu/stable-diffusion-webui'
        self.cmd = [
            "python", "launch.py",
            "--listen",
            "--port", str(self.port),
            "--device-id", str(self.device_id),
            "--enable-insecure-extension-access",
            "--api",
            "--api-log",
            "--log-startup",
            "--xformers",
            "--no-half-vae",
            "--no-download-sd-model",
            "--no-hashing",
            "--nowebui",
            "--skip-torch-cuda-test",
            "--skip-load-model-at-start",
            "--disable-safe-unpickle",
            "--skip-prepare-environment",
            "--skip-python-version-check",
            "--skip-install",
            "--skip-version-check",
            "--disable-nan-check",
        ]

        if service_type == 'comfy':
            self.cwd = '/home/ubuntu/ComfyUI'
            self.cmd = [
                "python", "main.py",
                "--listen", self.host,
                "--port", str(self.port),
                "--cuda-device", str(self.device_id),
            ]

        logger.info("Launching app on device %s, port: %s, command: %s", self.device_id, self.port, self.cmd)

        self.process = subprocess.Popen(
            self.cmd,
            cwd=self.cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        self.stdout_thread = threading.Thread(target=self._handle_output, args=(self.process.stdout, "STDOUT"))
        self.stderr_thread = threading.Thread(target=self._handle_output, args=(self.process.stderr, "STDERR"))

        self.stdout_thread.start()
        self.stderr_thread.start()

    def _handle_output(self, pipe, _):
        with pipe:
            for line in iter(pipe.readline, ''):
                if line.strip():
                    sys.stdout.write(f"{self.name}: {line}")

    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.stdout_thread.join()
            self.stderr_thread.join()

    def __del__(self):
        self.stop()

    def restart(self):
        logger.info("app process is going to restart")
        self.stop()
        self.start()

    def is_port_ready(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', self.port))
            return result == 0

    async def invocations(self, payload, infer_id=None):

        self.name = f"{service_type}-gpu{self.device_id}-{infer_id}"

        if 'task_index' in payload:
            self.name = f"{self.name}-{payload['task_index']}"

        try:
            self.busy = True
            payload['port'] = self.port
            url = f"http://127.0.0.1:{self.port}/invocations"
            timeout = aiohttp.ClientTimeout(total=300)

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=timeout) as response:
                    if response.status != 200:
                        result = json.dumps({
                            "status_code": response.status,
                            "detail": f"service returned an error: {await response.text()}"
                        })
                        self.busy = False
                        return result
                    response_data = await response.json()
            self.busy = False
            return response_data
        except Exception as e:
            self.busy = False
            logger.error(f"invocations error:{e}")
            return json.dumps({
                "status_code": 500,
                "detail": f"service returned an error: {str(e)}"
            })


apps: List[App] = []


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


def signal_handler(signum, frame):
    logger.info(f"Received signal {signum} ({signal.strsignal(signum)})")
    if signum in [signal.SIGINT, signal.SIGTERM]:
        global should_exit
        should_exit = 1
        sys.exit(0)


def setup_signal_handlers():
    catchable_sigs = set(signal.Signals) - {signal.SIGKILL, signal.SIGSTOP}
    for sig in catchable_sigs:
        try:
            signal.signal(sig, signal_handler)
        except Exception as exc:
            logger.info(f"Signal {sig} cannot be caught")


def get_poll_app():
    for sd_app in apps:
        if sd_app.process and sd_app.process.poll() is None:
            return sd_app
    return None


def get_all_available_apps():
    list: List[App] = []
    for app in apps:
        if app.is_port_ready() and not app.busy:
            list.append(app)

    return list


def get_available_app():
    apps = get_all_available_apps()

    if apps:
        return apps[0]

    return None


def start_apps(nums: int):
    logger.info(f"GPU count: {nums}")
    for device_id in range(nums):
        sd_app = App(device_id)
        sd_app.start()
        apps.append(sd_app)


def check_sync():
    logger.info("start check_sync!")
    while True:
        try:
            app = get_available_app()
            if app:
                logger.info("start check_sync! checking function-------")
                response = requests.post(f"http://127.0.0.1:{app.port}/sync_instance")
                logger.info(f"sync response:{response.json()} time : {datetime.datetime.now()}")

                logger.info("start check_reboot! checking function-------")
                response2 = requests.post(f"http://127.0.0.1:{app.port}/reboot")
                logger.info(f"reboot response:{response.json()} time : {datetime.datetime.now()}")
            time.sleep(SLEEP_TIME)
        except Exception as e:
            logger.info(f"check_sync error:{e}")
            time.sleep(SLEEP_TIME)


def check_apps():
    logger.info("start check apps!")
    while True:
        time.sleep(SLEEP_TIME)
        if should_exit:
            return
        try:
            logger.info(f"all_apps: {len(apps)} all_available_apps: {len(get_all_available_apps())}")
        except Exception as e:
            logger.info(f"check_and_reboot error:{e}")
            time.sleep(SLEEP_TIME)


@app.get("/ping")
async def ping():
    global should_exit
    if should_exit:
        await asyncio.sleep(1800)
        return Response(content="pong", status_code=status.HTTP_502_BAD_GATEWAY)
    return {"message": "pong"}


@app.post("/invocations")
async def invocations(request: Request):
    payload = await request.json()

    if service_type == 'sd':
        infer_id = payload['id']
    else:
        infer_id = payload['prompt_id']

    logger.info(f"controller_invocation {infer_id} received")

    while True:
        app = get_available_app()
        if app:
            return await app.invocations(payload=payload, infer_id=infer_id)
        else:
            await asyncio.sleep(1)
            logger.info(f'controller_invocation {infer_id} waiting for an available app...')


def stop():
    global should_exit
    should_exit = 1

    logger.info("stopping...")
    for cur_app in apps:
        cur_app.stop()


def check_endpoint():
    while True:
        time.sleep(10)
        if should_exit:
            return
        try:
            sagemaker.describe_endpoint(EndpointName=endpoint_name)
        except Exception as e:
            if 'Could not find endpoint' in str(e):
                logger.info(f"Endpoint {endpoint_name} not found, stopping...")
                stop()


def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")


if __name__ == "__main__":
    setup_signal_handlers()

    server = threading.Thread(target=run_server)
    server.start()

    gpu_nums = get_gpu_count()
    start_apps(gpu_nums)

    check_apps_thread = threading.Thread(target=check_apps, daemon=True)
    check_apps_thread.start()

    check_endpoint_thread = threading.Thread(target=check_endpoint, daemon=True)
    check_endpoint_thread.start()

    if service_type == 'comfy':
        queue_lock = threading.Lock()
        check_sync_thread = threading.Thread(target=check_sync, daemon=True)
        check_sync_thread.start()
