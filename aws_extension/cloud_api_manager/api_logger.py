import logging
import os
import markdown

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ApiLogger:
    action = ""
    infer_id = ""
    file_path = ""
    file_path_html = ""

    def __init__(self, action: str, append: bool = False, infer_id: str = ""):
        self.action = action
        self.infer_id = infer_id
        self.file_path = f'outputs/{infer_id}.md'
        self.file_path_html = f'outputs/{infer_id}.html'

        if append is False:
            self.file = open(self.file_path, 'w')
            self.file.write(f"# Inference Job API Request Process - {infer_id}\n")
        else:
            if os.path.exists(self.file_path):
                self.file = open(self.file_path, 'a')
            else:
                self.file = open(self.file_path, 'w')

    def req_log(self, sub_action: str, method: str, path: str, headers=None, data=None, params=None, response=None):
        self.file.write(f"## {sub_action}\n")
        self.file.write(f"\n")

        self.file.write(f"#### {method} {path}\n")
        self.file.write(f"\n")

        if headers:
            headers['x-api-key'] = '***'
            self.file.write(f"#### headers: \n")
            self.file.write(f"\n")
            self.file.write(f"```\n")
            self.file.write(f"{headers}\n")
            self.file.write(f"```\n")
            self.file.write(f"\n")
        if data:
            self.file.write(f"#### data:\n")
            self.file.write(f"\n")
            self.file.write(f"```\n")
            self.file.write(f"{data}\n")
            self.file.write(f"```\n")
            self.file.write(f"\n")
        if params:
            self.file.write(f"#### params: \n")
            self.file.write(f"\n")
            self.file.write(f"```\n")
            self.file.write(f"{params}\n")
            self.file.write(f"```\n")
            self.file.write(f"\n")
        if response:
            self.file.write(f"#### response:\n")
            self.file.write(f"\n")
            self.file.write(f"```\n")
            self.file.write(f"{response.json()}\n")
            self.file.write(f"```\n")
        self.file.write("\n")

        try:
            with open(self.file_path, 'r') as file:
                file_content = file.read()
                html = markdown.markdown(file_content)
                with open(self.file_path_html, 'w') as html_file:
                    html_file.write(html)
        except Exception as e:
            logger.error(e)
