from typing import Dict, List


def controlnet_args(script_name, arg, *_) -> Dict[str, List[str]]:
    if script_name != 'controlnet' or not arg.enabled:
        return {}

    model_name_parts = arg.model.split()
    models = []
    # make sure there is a hash, otherwise remain not changed
    if len(model_name_parts) > 1:
        arg.model = ' '.join(model_name_parts[:-1])

    if arg.model == 'None':
        return {}

    models.append(f'{arg.model}.pth')

    return {'ControlNet': models}