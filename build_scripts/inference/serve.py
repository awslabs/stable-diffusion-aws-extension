import logging
import signal
import socket
import subprocess
from time import sleep

import requests
import uvicorn
from fastapi import FastAPI, Request, HTTPException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
app = FastAPI()

COMFY_PORT = 8081


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
        if is_port_open(COMFY_PORT):
            req = await request.json()
            logger.info(f"invocations start req:{req}  url:http://127.0.0.1:{COMFY_PORT}/invocations")
            response = requests.post(f"http://127.0.0.1:{COMFY_PORT}/invocations", json=req)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code,
                                    detail=f"service returned an error: {response.text}")
            return response.json()
        else:
            sleep(1)
            logger.info('waiting for comfy service to start...')


def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', port))
        return result == 0


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_sigterm)
    subprocess.Popen(["bash", "/serve.sh"])
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
