import logging
import socket
import subprocess
from time import sleep

import requests
import uvicorn
from fastapi import FastAPI, Request, HTTPException

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
app = FastAPI()

PHY_LOCALHOST = '127.0.0.1'
COMFY_PORT = 8081


@app.get("/ping")
async def ping():
    return {"message": "pong"}


@app.post("/invocations")
async def invocations(request: Request):
    while True:
        if is_port_open('127.0.0.1', 8081):
            req = await request.json()
            logger.info(f"invocations start req:{req}  url:{PHY_LOCALHOST}:{COMFY_PORT}/invocations")
            response = requests.post(f"http://{PHY_LOCALHOST}:{COMFY_PORT}/invocations", json=req)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code,
                                    detail=f"service returned an error: {response.text}")
            return response.json()
        else:
            sleep(1)
            print('Waiting for port to be open')


def is_port_open(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        return result == 0


if __name__ == "__main__":
    subprocess.Popen(["bash", "/serve.sh"])
    uvicorn.run(app, host="0.0.0.0", port=8080)
