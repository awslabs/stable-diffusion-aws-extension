import logging
import os
import subprocess
from multiprocessing import Process

import requests
import uvicorn
from fastapi import APIRouter, FastAPI, Request, HTTPException

TIMEOUT_KEEP_ALIVE = 30
COMFY_PORT = 8181
SAGEMAKER_PORT = 8080
LOCALHOST = '0.0.0.0'
PHY_LOCALHOST = '127.0.0.1'

SLEEP_TIME = 30

app = FastAPI()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def invocations(request: Request):
    req = await request.json()
    logger.info(f"invocations start req:{req}  url:{PHY_LOCALHOST}:{COMFY_PORT}/invocations")
    response = requests.post(f"http://{PHY_LOCALHOST}:{COMFY_PORT}/invocations", json=req)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code,
                            detail=f"COMFY service returned an error: {response.text}")
    return response.json()


def ping():
    if os.environ.get('ALREADY_INIT') == 'false':
        raise HTTPException(status_code=500)
    else:
        return {'status': 'Healthy'}


class Api:
    def add_api_route(self, path: str, endpoint, **kwargs):
        return self.app.add_api_route(path, endpoint, **kwargs)

    def __init__(self, app: FastAPI):
        self.router = APIRouter()
        self.app = app
        self.add_api_route("/invocations", invocations, methods=["POST"])
        self.add_api_route("/ping", ping, methods=["GET"], response_model={})

    def launch(self, server_name, port):
        self.app.include_router(self.router)
        uvicorn.run(self.app, host=server_name, port=port, timeout_keep_alive=TIMEOUT_KEEP_ALIVE)


class ComfyApp:
    def __init__(self, host=LOCALHOST, port=COMFY_PORT):
        self.host = host
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


if __name__ == "__main__":
    api = Api(app)

    comfy_app = ComfyApp()
    api_process = Process(target=api.launch, args=(LOCALHOST, SAGEMAKER_PORT))

    # check_reboot_thread = threading.Thread(target=check_reboot)

    comfy_app.start()
    api_process.start()
    subprocess.Popen(["bash", "/serve.sh"])

    # check_reboot_thread.start()

    api_process.join()

    # check_sync_thread.join()
    # check_reboot_thread.join()
