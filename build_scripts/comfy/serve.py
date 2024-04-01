import datetime
import logging
import os
import subprocess
import threading
import time
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

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.INFO)


async def invocations(request: Request):
    req = await request.json()
    logger.info(f"invocations start req:{req}  url:{PHY_LOCALHOST}:{COMFY_PORT}/invocations")
    response = requests.post(f"http://{PHY_LOCALHOST}:{COMFY_PORT}/invocations", json=req)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code,
                            detail=f"COMFY service returned an error: {response.text}")
    return response.json()


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
    def __init__(self, host=LOCALHOST, port=COMFY_PORT):
        self.host = host
        self.port = port
        self.process = None

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
        if self.process and self.process.poll() is None:
            os.environ['ALREADY_INIT'] = 'false'
            self.process.terminate()
            self.process.wait()
        self.start()


# def start_comfy_app(host=LOCALHOST, port=COMFY_PORT):
#     cmd = "python main.py  --listen {} --port {}".format(host, port)
#     os.system(cmd)
def check_and_reboot():
    logger.info("start check_and_reboot!")
    while True:
        logger.info("start check_and_reboot! checking server-------")
        try:
            logger.info("start check_and_reboot! checking function-------")
            response = requests.post(f"http://{PHY_LOCALHOST}:{COMFY_PORT}/sync_instance")
            logger.info(f"sync response:{response} time : {datetime.datetime.now()}")
            need_reboot = os.environ.get('NEED_REBOOT')
            logger.info(f'need_reboot value check: {need_reboot} ！')
            # for key, value in os.environ.items():
            #     logger.info(f"{key}: {value}")
            if need_reboot and need_reboot.lower() == 'true':
                os.environ['NEED_REBOOT'] = 'false'
                logger.info(f'need_reboot, reboot  start!')
                comfy_app.restart()
                logger.info(f'need_reboot, reboot  finished!')
            time.sleep(60 * 1)
        except Exception as e:
            logger.info(f"check_and_reboot error:{e}")
            time.sleep(10)





if __name__ == "__main__":
    queue_lock = threading.Lock()
    api = Api(app, queue_lock)

    # api_process = Process(target=api.launch, args=(LOCALHOST, SAGEMAKER_PORT))
    # comfy_process = Process(target=start_comfy_app, args=(LOCALHOST, COMFY_PORT))
    #
    # comfy_process.start()
    # api_process.start()
    #
    # comfy_process.join()
    # api_process.join()

    comfy_app = ComfyApp()
    api_process = Process(target=api.launch, args=(LOCALHOST, SAGEMAKER_PORT))

    check_thread = threading.Thread(target=check_and_reboot)

    comfy_app.start()
    api_process.start()
    check_thread.start()

    api_process.join()
    check_thread.join()


