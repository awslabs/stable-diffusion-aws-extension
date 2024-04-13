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
from time import sleep
from typing import List

import requests
import uvicorn
from fastapi import FastAPI, Request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Controller")
logger.setLevel(logging.INFO)
app = FastAPI()
SLEEP_TIME = 30
service_type = os.getenv('SERVICE_TYPE', 'sd')


class SdApp:
    def __init__(self, device_id):
        self.host = "127.0.0.1"
        self.device_id = device_id
        self.port = 24000 + device_id
        self.name = f"{service_type}-{self.port}-gpu{device_id}"
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
                "--cuda_device", str(self.device_id),
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
        prefix = f"{self.name}: "
        with pipe:
            for line in iter(pipe.readline, ''):
                sys.stdout.write(prefix + line)

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

    def is_ready(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', self.port))
            return result == 0

    def invocations(self, payload):
        try:
            app.busy = True
            payload['port'] = self.port
            logger.info(f"invocations start req: http://127.0.0.1:{self.port}/invocations")
            response = requests.post(f"http://127.0.0.1:{self.port}/invocations", json=payload, timeout=(200, 300))
            if response.status_code != 200:
                return json.dumps({
                    "status_code": response.status_code,
                    "detail": f"service returned an error: {response.text}"
                })
            app.busy = False
            return response.json()
        except Exception as e:
            app.busy = False
            logger.error(f"invocations error:{e}")
            return json.dumps({
                "status_code": 500,
                "detail": f"service returned an error: {str(e)}"
            })


apps: List[SdApp] = []


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


def handle_sigterm(signum, frame):
    logger.info("SIGTERM received, performing cleanup...")
    logger.info(signum)
    logger.info(frame)


@app.get("/ping")
async def ping():
    return {"message": "pong"}


@app.post("/invocations")
async def invocations(request: Request):
    while True:
        app = get_available_app()
        if app and not app.busy:
            return app.invocations(await request.json())
        else:
            sleep(2)
            logger.info('an invocation waiting for an available app...')


def get_poll_app():
    for sd_app in apps:
        if sd_app.process and sd_app.process.poll() is None:
            return sd_app
    return None


def get_available_app():
    app = get_poll_app()
    if app and app.is_ready():
        return app

    return None


def start_apps(nums: int):
    logger.info(f"GPU count: {nums}")
    for device_id in range(nums):
        sd_app = SdApp(device_id)
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
            logger.info(f"check_and_reboot error:{e}")
            time.sleep(SLEEP_TIME)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_sigterm)
    gpu_nums = get_gpu_count()
    start_apps(gpu_nums)
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")

    if service_type == 'comfy':
        queue_lock = threading.Lock()
        check_sync_thread = threading.Thread(target=check_sync)
        check_sync_thread.start()
