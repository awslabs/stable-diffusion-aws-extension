import json
import logging
import os

import markdown

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ApiLogger:
    action = ""
    infer_id = ""
    title = ""
    file_path = ""
    file_path_html = ""
    template_html = ""

    def __init__(self, action: str, append: bool = False, infer_id: str = ""):

        # if outputs dir not exists, create it
        if not os.path.exists('outputs'):
            os.makedirs('outputs')

        self.action = action
        self.infer_id = infer_id
        self.file_path = f'outputs/{infer_id}.md'
        self.file_path_html = f'outputs/{infer_id}.html'
        self.template_html = f'extensions/stable-diffusion-aws-extension/aws_extension/cloud_api_manager/api.html'
        self.title = f'Inference Job API Request Process - {infer_id}'

        if append is False:
            self.file = open(self.file_path, 'w')
            self.file.write(f"# {self.title}\n")
        else:
            if os.path.exists(self.file_path):
                self.file = open(self.file_path, 'a')
            else:
                self.file = open(self.file_path, 'w')

    def req_log(self, sub_action: str, method: str, path: str, headers=None, data=None, params=None, response=None,
                desc: str = ""):
        self.file.write(f"## {sub_action}\n")
        self.file.write(f"_{desc}_\n")
        self.file.write(f"\n")

        self.file.write(f"##### {method} {path}\n")
        self.file.write(f"\n")

        if headers:
            headers['x-api-key'] = 'xxxx'
            self.file.write(f"#### headers: \n")
            self.file.write(f"\n")
            self.file.write(f"```\n")
            self.file.write(f"{json.dumps(headers)}\n")
            self.file.write(f"```\n")
            self.file.write(f"\n")
        if data:
            self.file.write(f"#### data:\n")
            self.file.write(f"\n")
            self.file.write(f"```\n")
            if isinstance(data, str):
                self.file.write(f"{json.dumps(json.loads(data))}\n")
            else:
                self.file.write(f"{json.dumps(data)}\n")
            self.file.write(f"```\n")
            self.file.write(f"\n")
        if params:
            self.file.write(f"#### params: \n")
            self.file.write(f"\n")
            self.file.write(f"```\n")
            self.file.write(f"{json.dumps(params)}\n")
            self.file.write(f"```\n")
            self.file.write(f"\n")
        if response:
            self.file.write(f"#### response:\n")
            self.file.write(f"\n")
            self.file.write(f"```\n")
            self.file.write(f"{json.dumps(response.json())}\n")
            self.file.write(f"```\n")
        self.file.write("\n")

        try:
            with open(self.file_path, 'r') as file:
                file_content = file.read()
                html = markdown.markdown(file_content)
                html_content = self.generate_html(html)
                with open(self.file_path_html, 'w') as html_file:
                    html_file.write(html_content)
        except Exception as e:
            logger.error(e)

    def generate_html(self, content: str):
        try:
            with open(self.template_html, 'r') as file:
                file_content = file.read()
                file_content = file_content.replace("{{content}}", content)
                file_content = file_content.replace("{{title}}", self.title)
                return file_content
        except Exception as e:
            logger.error(e)
            return content

