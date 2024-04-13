import json
import logging
import os
import signal
import socket
import subprocess
from time import sleep

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

    def start(self):
        cmd = ["python", "main.py", "--listen", self.host, "--port", str(self.port)]
        self.process = subprocess.Popen(cmd)
        os.environ['ALREADY_INIT'] = 'true'

    def restart(self):
        logger.info("Comfy app process is going to restart")
        if self.process and self.process.poll() is None:
            os.environ['ALREADY_INIT'] = 'false'
            self.process.terminate()
            self.process.wait()
        self.start()


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
        if is_port_open(SERVER_PORT):
            try:
                req = await request.json()
                req['port'] = SERVER_PORT
                logger.info(f"invocations start req:{req} url:http://127.0.0.1:{SERVER_PORT}/invocations")
                response = requests.post(f"http://127.0.0.1:{SERVER_PORT}/invocations", json=req, timeout=(200, 300))
                if response.status_code != 200:
                    return json.dumps({
                        "status_code": response.status_code,
                        "detail": f"service returned an error: {response.text}"
                    })
                return response.json()
            except Exception as e:
                logger.error(f"invocations error:{e}")
                return json.dumps({
                    "status_code": 500,
                    "detail": f"service returned an error: {str(e)}"
                })
        else:
            sleep(2)
            logger.info('an invocation waiting for service to start...')


def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', port))
        return result == 0


if __name__ == "__main__":
    print("GPU count:", get_gpu_count())
    signal.signal(signal.SIGTERM, handle_sigterm)
    subprocess.Popen(["bash", "/serve.sh"])
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
