from typing import Dict, List


def xyz_args(script_name, arg, current_index, args, cache, is_txt2img):
    if script_name != 'x/y/z plot':
        return {}, None

    if not arg or type(arg) is not list:
        return {}, None

    # 11 represent the checkpoint_name (sd only) option for both img2img and txt2img
    # ref: xyz_grid.py#L244
    if current_index - 2 < 0:
        return {}, None

    if is_txt2img and (args[current_index - 2] == 11 or args[current_index - 2] == 35):
        return {'Stable-diffusion': arg}, None

    elif is_txt2img and (args[current_index - 2] == 39):
        models = []
        for filename in cache['controlnet']:
            for model_without_type in arg:
                if filename.startswith(model_without_type):
                    models.append(filename)
        return {'ControlNet': models}, None

    elif is_txt2img and (args[current_index - 2] == 27):
        return {'VAE': arg}, None

    elif not is_txt2img and (args[current_index - 2] == 10 or args[current_index - 2] == 34):
        return {'Stable-diffusion': arg}, None

    elif not is_txt2img and (args[current_index - 2] == 38):
        models = []
        for filename in cache['controlnet']:
            for model_without_type in arg:
                if filename.startswith(model_without_type):
                    models.append(filename)
        return {'ControlNet': models}, None

    elif not is_txt2img and (args[current_index - 2] == 26):
        return {'VAE': arg}, None

    return {}, None
