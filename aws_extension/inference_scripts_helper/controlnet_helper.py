import os
from typing import Dict, List


def controlnet_args(script_name, arg, *_) -> Dict[str, List[str]]:
    if script_name != 'controlnet' or not arg.enabled:
        return {}, None

    model_name_parts = arg.model.split()
    models = []
    # make sure there is a hash, otherwise remain not changed
    if len(model_name_parts) > 1:
        arg.model = ' '.join(model_name_parts[:-1])

    if arg.model == 'None':
        return {}, None

    cn_models_dir = os.path.join("models", "ControlNet")

    for filename in os.listdir(cn_models_dir):
        if filename.startswith(arg.model):
            models.append(filename)

    return {'ControlNet': models}, None
