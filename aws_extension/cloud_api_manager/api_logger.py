import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ApiLogger:
    action = ""

    def __init__(self, action: str, action_id=str):
        self.action = action
        # create file and open to write txt
        self.file = open(f'{action}.txt', 'w')
        self.file.write(f"action: {self.action}\n")

    def req_log(self, sub_action: str, method: str, path: str, headers=None, data=None, params=None):
        self.file.write(f"sub_action: {sub_action}\n")
        self.file.write(f"method: {method}\n")
        self.file.write(f"path: {path}\n")
        self.file.write(f"headers: {headers}\n")
        self.file.write(f"data: {data}\n")
        self.file.write(f"params: {params}\n")

