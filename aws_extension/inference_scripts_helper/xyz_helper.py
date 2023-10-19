from typing import Dict, List


def xyz_args(script_name, arg, current_index, args) -> Dict[str, List[str]]:
    if script_name != 'x/y/z plot':
        return {}, None

    if not arg or type(arg) is not list:
        return {}, None

    # 10 represent the checkpoint_name option for both img2img and txt2img
    # ref: xyz_grid.py#L204
    if current_index - 2 < 0 or args[current_index - 2] != 10:
        return {}, None

    models = [' '.join(md.split()[:-1]) for md in arg]
    for _id, val in enumerate(models):
        args[current_index][_id] = val

    return {'Stable-diffusion': models}, None
