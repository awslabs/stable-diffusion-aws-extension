import os
from typing import Dict, List


def controlnet_args(script_name, arg, current_index, args, cache) -> Dict[str, List[str]]:
    if script_name != 'controlnet' or not arg.enabled:
        return {}, None

    model_name_parts = arg.model.split()
    models = []
    # make sure there is a hash, otherwise remain not changed
    if len(model_name_parts) > 1:
        arg.model = ' '.join(model_name_parts[:-1])

    if arg.model == 'None':
        return {}, None

    for filename in cache['controlnet']:
        if filename.startswith(arg.model):
            models.append(filename)

    return {'ControlNet': models}, None
