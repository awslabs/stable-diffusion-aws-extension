from aws_extension.inference_scripts_helper import controlnet_helper, xyz_helper, refiner_helper


def process_args_by_plugin(p, script_name, arg, current_index, args):
    processors = {
        'controlnet': controlnet_helper.controlnet_args,
        'x/y/z plot': xyz_helper.xyz_args,
        'refiner': refiner_helper.refiner_args,
    }
    models = {}
    if script_name not in processors:
        return arg, models

    f = processors[script_name]
    mdls, arg_modified = f(script_name, arg, current_index, args)
    if arg_modified is not None:
        arg = arg_modified
        p.refiner_checkpoint = None
        p.refiner_switch_at = None
    for key, val in mdls.items():
        if not val:
            continue

        if key not in models:
            models[key] = []

        models[key].extend(val)

    return arg, models