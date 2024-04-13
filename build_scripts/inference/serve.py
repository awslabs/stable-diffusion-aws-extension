import json
import logging
import os
import signal
import socket
import subprocess
import sys
from time import sleep
from typing import List

import requests
import uvicorn
from fastapi import FastAPI, Request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("controller")
logger.setLevel(logging.INFO)
app = FastAPI()

service_type = os.getenv('SERVICE_TYPE', 'sd')
SD_PORT = os.getenv('SD_PORT', 24001)
COMFY_PORT = 8081

SERVER_PORT = COMFY_PORT if service_type == 'comfy' else SD_PORT


class SdApp:
    def __init__(self, port):
        self.host = "127.0.0.1"
        self.port = port
        self.process = None
        self.busy = False

    def start(self):
        cmd = [
            "python", "main.py",
            "--listen", self.host,
            "--port", str(self.port),
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
        self.process = subprocess.Popen(
            cmd,
            cwd='/home/ubuntu/stable-diffusion-webui',
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        os.environ['ALREADY_INIT'] = 'true'

    def restart(self):
        logger.info("Comfy app process is going to restart")
        if self.process and self.process.poll() is None:
            os.environ['ALREADY_INIT'] = 'false'
            self.process.terminate()
            self.process.wait()
        self.start()

    def is_ready(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', self.port))
            return result == 0


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
    logger.info("invocation received...")
    while True:
        app = get_available_app()
        if app and not app.busy:
            try:
                app.busy = True
                req = await request.json()
                req['port'] = app.port
                logger.info(f"invocations start req:{req} url:http://127.0.0.1:{app.port}/invocations")
                response = requests.post(f"http://127.0.0.1:{app.port}/invocations", json=req, timeout=(200, 300))
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
    for i in range(nums):
        sd_app = SdApp(24000 + i)
        sd_app.start()
        apps.append(sd_app)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_sigterm)
    gpu_nums = get_gpu_count()
    start_apps(gpu_nums)
    # subprocess.Popen(["bash", "/serve.sh"])
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
