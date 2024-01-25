import logging

import gradio

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ApiLogger:
    action = ""

    def __init__(self, action: str, append: bool = False, username: str = ""):
        self.action = action
        file_path = f'extensions/stable-diffusion-aws-extension/{action}-{username}.txt'
        if append is False:
            self.file = open(file_path, 'w')
        else:
            self.file = open(file_path, 'a')

    def req_log(self, sub_action: str, method: str, path: str, headers=None, data=None, params=None, response=None):
        self.file.write(f"sub_action: {sub_action}\n")
        self.file.write(f"method: {method}\n")
        self.file.write(f"path: {path}\n")
        if headers:
            self.file.write(f"headers: {headers}\n")
        if data:
            self.file.write(f"data: {data}\n")
        if params:
            self.file.write(f"params: {params}\n")
        if response:
            self.file.write(f"response: {response.json()}\n")
        self.file.write("\n")
        self.file.write("\n")
