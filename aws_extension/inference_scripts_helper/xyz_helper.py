from typing import Dict, List


def xyz_args(script_name, arg, current_index, args, _):
    if script_name != 'x/y/z plot':
        return {}, None

    if not arg or type(arg) is not list:
        return {}, None

    # 11 represent the checkpoint_name (sd only) option for both img2img and txt2img
    # ref: xyz_grid.py#L244
    if current_index - 2 < 0:
        return {}, None
    if args[current_index - 2] == 11:
        return {'Stable-diffusion': arg}, None

    return {}, None
