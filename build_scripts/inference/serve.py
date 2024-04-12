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


def handle_sigterm(signum, frame):
    logger.info("SIGTERM received, performing cleanup...")
    logger.info(signum)
    logger.info(frame)


@app.get("/ping")
async def ping():
    return {"message": "pong"}


@app.post("/invocations")
async def invocations(request: Request):
    logger.info("invocations start")
    while True:
        if is_port_open(SERVER_PORT):
            try:
                req = await request.json()
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
            sleep(1)
            logger.info('waiting for service to start...')


def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', port))
        return result == 0


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_sigterm)
    subprocess.Popen(["bash", "/serve.sh"])
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
