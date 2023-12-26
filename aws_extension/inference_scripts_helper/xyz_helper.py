from typing import Dict, List

IMG_XYZ_CHECKPOINT_INDEX = 10
TXT_XYZ_CHECKPOINT_INDEX = 11

IMG_XYZ_REFINER_CHECKPOINT_INDEX = 34
TXT_XYZ_REFINER_CHECKPOINT_INDEX = 35

IMG_XYZ_VAE_INDEX = 26
TXT_XYZ_VAE_INDEX = 27

IMG_XYZ_CONTROLNET_INDEX = 38
TXT_XYZ_CONTROLNET_INDEX = 39

def xyz_args(script_name, arg, current_index, args, cache, is_txt2img):
    if script_name != 'x/y/z plot':
        return {}, None

    if not arg or type(arg) is not list:
        return {}, None

    # 11 represent the checkpoint_name (sd only) option for both img2img and txt2img
    # ref: xyz_grid.py#L244
    if current_index - 2 < 0:
        return {}, None

    if is_txt2img and (args[current_index - 2] == TXT_XYZ_CHECKPOINT_INDEX
                       or args[current_index - 2] == TXT_XYZ_REFINER_CHECKPOINT_INDEX):
        return {'Stable-diffusion': arg}, None

    elif is_txt2img and (args[current_index - 2] == TXT_XYZ_CONTROLNET_INDEX):
        models = []
        for filename in cache['controlnet']:
            for model_without_type in arg:
                if filename.startswith(model_without_type):
                    models.append(filename)
        return {'ControlNet': models}, None

    elif is_txt2img and (args[current_index - 2] == TXT_XYZ_VAE_INDEX):
        return {'VAE': arg}, None

    elif not is_txt2img and (args[current_index - 2] == IMG_XYZ_CHECKPOINT_INDEX
                             or args[current_index - 2] == IMG_XYZ_REFINER_CHECKPOINT_INDEX):
        return {'Stable-diffusion': arg}, None

    elif not is_txt2img and (args[current_index - 2] == IMG_XYZ_CONTROLNET_INDEX):
        models = []
        for filename in cache['controlnet']:
            for model_without_type in arg:
                if filename.startswith(model_without_type):
                    models.append(filename)
        return {'ControlNet': models}, None

    elif not is_txt2img and (args[current_index - 2] == IMG_XYZ_VAE_INDEX):
        return {'VAE': arg}, None

    return {}, None
