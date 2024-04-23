import os
import subprocess
import threading
from dataclasses import dataclass

from aiohttp import web

import server


@dataclass
class Response:
    message: str
    reload_timeout: int = None

    def to_json(self):
        return {"message": self.message, "reload_timeout": self.reload_timeout}


service_file = "/etc/systemd/system/comfy.service"
service_file_not_found = (f"Service file {service_file} not found, "
                          f"make sure you created the service by CloudFormation template.")
command_latency = 3
reload_timeout = (command_latency + 1) * 1000


def run_reboot():
    subprocess.run(["sleep", command_latency])
    subprocess.run(["sudo", "reboot"])


def run_restart():
    subprocess.run(["sleep", command_latency])
    subprocess.run(["sudo", "systemctl", "restart", "comfy.service"])


@server.PromptServer.instance.routes.get("/reboot")
async def reboot_ec2(self):
    if not os.path.exists(service_file):
        return web.json_response(Response(service_file_not_found).to_json())

    thread = threading.Thread(target=run_reboot)
    thread.start()
    return web.json_response(Response("Rebooting EC2, Please wait...", reload_timeout).to_json())


@server.PromptServer.instance.routes.get("/restart")
async def restart_comfy(self):
    if not os.path.exists(service_file):
        return web.json_response(Response(service_file_not_found).to_json())

    thread = threading.Thread(target=run_restart)
    thread.start()
    return web.json_response(Response("Restarting Comfy, Please wait...", reload_timeout).to_json())
