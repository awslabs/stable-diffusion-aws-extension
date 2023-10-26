from typing import List, Dict
from aws_extension.sagemaker_ui import None_Option_For_On_Cloud_Model


def refiner_args(script_name, arg, current_index, args, _) -> Dict[str, List[str]]:
    if script_name != 'refiner':
        return {}, None

    # the refiner plugin has 3 args
    # index 0 is enabled or not, it's a bool
    # index 1 is the stable diffusion model name
    # index 2 is a number, but not important here
    if args[1] == None_Option_For_On_Cloud_Model:
        args = (False, "") + args[2:]
        if arg is True:
            return {}, False
        elif arg == None_Option_For_On_Cloud_Model:
            return {}, ""

    if current_index == 0:
        if args[0]:
            return {'Stable-diffusion': [args[1]]}, None

    return {}, None
