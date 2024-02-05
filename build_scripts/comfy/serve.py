import os
import threading
from multiprocessing import Process
from threading import Lock

import requests
import uvicorn
from fastapi import APIRouter, FastAPI, Request, HTTPException

TIMEOUT_KEEP_ALIVE = 30
COMFY_PORT = 8188
SAGEMAKER_PORT = 8080
LOCALHOST = '0.0.0.0'
PHY_LOCALHOST = '127.0.0.1'

app = FastAPI()


async def invocations(request: Request):
    req = await request.json()
    print(f"invocations start req:{req}  url:{PHY_LOCALHOST}:{COMFY_PORT}/invocations")
    response = requests.post(f"http://{PHY_LOCALHOST}:{COMFY_PORT}/invocations", json=req)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code,
                            detail=f"COMFY service returned an error: {response.text}")
    return {"message": "Invocations endpoint"}


def ping():
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


def start_comfy_app(host=LOCALHOST, port=COMFY_PORT):
    cmd = "python main.py  --listen {} --port {}".format(host, port)
    os.system(cmd)


if __name__ == "__main__":
    queue_lock = threading.Lock()
    api = Api(app, queue_lock)

    api_process = Process(target=api.launch, args=(LOCALHOST, SAGEMAKER_PORT))
    comfy_process = Process(target=start_comfy_app, args=(LOCALHOST, COMFY_PORT))

    comfy_process.start()
    api_process.start()

    comfy_process.join()
    api_process.join()
