import os
import sys
from modules.paths_internal import script_path, models_path, data_path



# data_path = cmd_opts_pre.data
sys.path.insert(0, script_path)

path_dirs = [
    (os.path.join(script_path, 'repositories/stable-diffusion-stability-ai'), 'ldm', 'Stable Diffusion', []),
    (os.path.join(script_path, 'repositories/CodeFormer'), 'inference_codeformer.py', 'CodeFormer', []),
    ]

paths = {}

for d, must_exist, what, options in path_dirs:
    must_exist_path = os.path.abspath(os.path.join(script_path, d, must_exist))
    if not os.path.exists(must_exist_path):
        print(f"Warning: {what} not found at path {must_exist_path}", file=sys.stderr)
    else:
        d = os.path.abspath(d)
        if "atstart" in options:
            sys.path.insert(0, d)
        else:
            sys.path.append(d)
        paths[what] = d
