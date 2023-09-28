from typing import List, Dict


def refiner_args(script_name, _, current_index, args) -> Dict[str, List[str]]:
    if script_name != 'refiner':
        return {}

    # the refiner plugin has 3 args
    # index 0 is enabled or not, it's a bool
    # index 1 is the stable diffusion model name
    # index 2 is a number, but not important here

    if current_index == 0:
        if args[0]:
            return {'Stable-diffusion': [args[1]]}

    return {}
