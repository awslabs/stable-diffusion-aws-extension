import logging
import os
import shutil

import requests
from modules import scripts, sd_models, shared
from utils import get_variable_from_json, has_config

postfix = 'SageMaker'
sapi_dir = os.path.join(scripts.basedir(), 'aws_extension', 'cloud_models_manager')


class CloudSDModelsManager:

    sapi_dir = scripts.basedir()

    def __init__(self):
        self.model_type = 'Stable-diffusion'
        self.ckpt_lookup_by_name = {}
        self.clear()

    def update_models(self):
        model_list = self._fetch_models_list()
        try:
            for model_name in model_list:
                shutil.copy2(os.path.join(sapi_dir, 'Dummy.safetensors'),
                             os.path.join(sd_models.model_path,
                                          '.'.join(model_name.split('.')[:-1]) + f'.{postfix}.safetensors'))

        except Exception as e:
            print(f"update_models Error: {e}")
        shared.refresh_checkpoints()
        sd_models.list_models()

    def _fetch_models_list(self):
        try:
            api_gateway_url = get_variable_from_json('api_gateway_url')
            if not has_config():
                print(f"Please config api_gateway_url and api_token")
                return []
            api_url = f'{api_gateway_url}checkpoints?status=Active&types={self.model_type}'
            api_key_header = {'x-api-key': get_variable_from_json('api_token')}

            raw_resp = requests.get(url=api_url, headers=api_key_header)
            raw_resp.raise_for_status()

            json_resp = raw_resp.json()
            if 'checkpoints' not in json_resp.keys():
                return []

            checkpoint_list = []
            for ckpt in json_resp['checkpoints']:
                if 'name' not in ckpt or not ckpt['name']:
                    continue

                for ckpt_name in ckpt['name']:
                    self.ckpt_lookup_by_name[ckpt_name] = ckpt
                    checkpoint_list.append(ckpt_name)

            return checkpoint_list
        except Exception as e:
            logging.error(e)
            return []

    def get_ckpt_s3_by_name(self, name):
        ckpt = self.ckpt_lookup_by_name[name]
        if ckpt:
            return f'{ckpt["s3Location"]}/{ckpt["name"]}'

        return ""

    def clear(self):
        for filename in os.listdir(sd_models.model_path):
            if f"{postfix}.safetensors" in filename:
                os.remove(os.path.join(sd_models.model_path, filename))
        self.ckpt_lookup_by_name.clear()
        pass


