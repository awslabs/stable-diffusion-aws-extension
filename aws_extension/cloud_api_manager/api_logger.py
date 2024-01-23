import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ApiLogger:
    action = ""

    def __init__(self, action: str, action_id=str):
        self.action = action
        self.action_id = action_id

    def req_log(self, sub_action: str, method: str, path: str, headers=None, data=None, params=None):
        print(f"sub_action: {sub_action}")
