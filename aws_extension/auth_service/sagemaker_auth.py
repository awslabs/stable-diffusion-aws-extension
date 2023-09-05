import os

from modules import scripts

auth_config_filename = 'sagemaker_auth.config'
config_path = os.path.join(scripts.basedir(), auth_config_filename)


class CloudAuthLoader:

    def __init__(self):
        self.clear()

    def create_config(self):
        with open(config_path, 'w+') as f:
            f.write('cyanda:password,alvindaiyan:password')

    def clear(self):
        if os.path.isfile(config_path):
            os.remove(config_path)
