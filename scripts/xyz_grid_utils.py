from collections import namedtuple
from copy import copy
from itertools import permutations, chain
import random
import csv
import os.path
from io import StringIO
from PIL import Image
import numpy as np

import modules.scripts as scripts
import gradio as gr

from modules import images, sd_samplers, processing, sd_models, sd_vae, sd_samplers_kdiffusion, errors
from modules.processing import process_images, Processed, StableDiffusionProcessingTxt2Img
from modules.shared import opts, state
import modules.shared as shared
import modules.sd_samplers
import modules.sd_models
import modules.sd_vae
import re
from scripts.global_state import update_cn_models, cn_models_names, cn_preprocessor_modules
from scripts.external_code import ResizeMode, ControlMode

from modules.ui_components import ToolButton

fill_values_symbol = "\U0001f4d2"  # 📒

AxisInfo = namedtuple('AxisInfo', ['axis', 'values'])



def apply_field(field):
    def fun(p, x, xs):
        setattr(p, field, x)

    return fun


def apply_prompt(p, x, xs):
    if xs[0] not in p.prompt and xs[0] not in p.negative_prompt:
        raise RuntimeError(f"Prompt S/R did not find {xs[0]} in prompt or negative prompt.")

    p.prompt = p.prompt.replace(xs[0], x)
    p.negative_prompt = p.negative_prompt.replace(xs[0], x)


def apply_order(p, x, xs):
    token_order = []

    # Initally grab the tokens from the prompt, so they can be replaced in order of earliest seen
    for token in x:
        token_order.append((p.prompt.find(token), token))

    token_order.sort(key=lambda t: t[0])

    prompt_parts = []

    # Split the prompt up, taking out the tokens
    for _, token in token_order:
        n = p.prompt.find(token)
        prompt_parts.append(p.prompt[0:n])
        p.prompt = p.prompt[n + len(token):]

    # Rebuild the prompt with the tokens in the order we want
    prompt_tmp = ""
    for idx, part in enumerate(prompt_parts):
        prompt_tmp += part
        prompt_tmp += x[idx]
    p.prompt = prompt_tmp + p.prompt


def confirm_samplers(p, xs):
    for x in xs:
        if x.lower() not in sd_samplers.samplers_map:
            raise RuntimeError(f"Unknown sampler: {x}")


def apply_checkpoint(p, x, xs):
    info = modules.sd_models.get_closet_checkpoint_match(x)
    if info is None:
        raise RuntimeError(f"Unknown checkpoint: {x}")
    p.override_settings['sd_model_checkpoint'] = info.name


def confirm_checkpoints(p, xs):
    for x in xs:
        if modules.sd_models.get_closet_checkpoint_match(x) is None:
            raise RuntimeError(f"Unknown checkpoint: {x}")


def confirm_checkpoints_or_none(p, xs):
    for x in xs:
        if x in (None, "", "None", "none"):
            continue

        if modules.sd_models.get_closet_checkpoint_match(x) is None:
            raise RuntimeError(f"Unknown checkpoint: {x}")


def apply_clip_skip(p, x, xs):
    opts.data["CLIP_stop_at_last_layers"] = x


def apply_upscale_latent_space(p, x, xs):
    if x.lower().strip() != '0':
        opts.data["use_scale_latent_for_hires_fix"] = True
    else:
        opts.data["use_scale_latent_for_hires_fix"] = False


def find_vae(name: str):
    if name.lower() in ['auto', 'automatic']:
        return modules.sd_vae.unspecified
    if name.lower() == 'none':
        return None
    else:
        choices = [x for x in sorted(modules.sd_vae.vae_dict, key=lambda x: len(x)) if name.lower().strip() in x.lower()]
        if len(choices) == 0:
            print(f"No VAE found for {name}; using automatic")
            return modules.sd_vae.unspecified
        else:
            return modules.sd_vae.vae_dict[choices[0]]


def apply_vae(p, x, xs):
    modules.sd_vae.reload_vae_weights(shared.sd_model, vae_file=find_vae(x))


def apply_styles(p: StableDiffusionProcessingTxt2Img, x: str, _):
    p.styles.extend(x.split(','))


def apply_uni_pc_order(p, x, xs):
    opts.data["uni_pc_order"] = min(x, p.steps - 1)


def apply_face_restore(p, opt, x):
    opt = opt.lower()
    if opt == 'codeformer':
        is_active = True
        p.face_restoration_model = 'CodeFormer'
    elif opt == 'gfpgan':
        is_active = True
        p.face_restoration_model = 'GFPGAN'
    else:
        is_active = opt in ('true', 'yes', 'y', '1')

    p.restore_faces = is_active


def apply_override(field, boolean: bool = False):
    def fun(p, x, xs):
        if boolean:
            x = True if x.lower() == "true" else False
        p.override_settings[field] = x
    return fun


def boolean_choice(reverse: bool = False):
    def choice():
        return ["False", "True"] if reverse else ["True", "False"]
    return choice


def format_value_add_label(p, opt, x):
    if type(x) == float:
        x = round(x, 8)

    return f"{opt.label}: {x}"


def format_value(p, opt, x):
    if type(x) == float:
        x = round(x, 8)
    return x


def format_value_join_list(p, opt, x):
    return ", ".join(x)


def do_nothing(p, x, xs):
    pass


def format_nothing(p, opt, x):
    return ""


def format_remove_path(p, opt, x):
    return os.path.basename(x)


def str_permutations(x):
    """dummy function for specifying it in AxisOption's type when you want to get a list of permutations"""
    return x


def list_to_csv_string(data_list):
    with StringIO() as o:
        csv.writer(o).writerow(data_list)
        return o.getvalue().strip()


def csv_string_to_list_strip(data_str):
    return list(map(str.strip, chain.from_iterable(csv.reader(StringIO(data_str)))))


def identity(x):
    return x


class ListParser():
    """This class restores a broken list caused by the following process
    in the xyz_grid module.
        -> valslist = [x.strip() for x in chain.from_iterable(
                                            csv.reader(StringIO(vals)))]
    It also performs type conversion,
    adjusts the number of elements in the list, and other operations.

    This class directly modifies the received list.
    """
    numeric_pattern = {
        int: {
            "range": r"\s*([+-]?\s*\d+)\s*-\s*([+-]?\s*\d+)(?:\s*\(([+-]\d+)\s*\))?\s*",
            "count": r"\s*([+-]?\s*\d+)\s*-\s*([+-]?\s*\d+)(?:\s*\[(\d+)\s*\])?\s*"
        },
        float: {
            "range": r"\s*([+-]?\s*\d+(?:\.\d*)?)\s*-\s*([+-]?\s*\d+(?:\.\d*)?)(?:\s*\(([+-]\d+(?:\.\d*)?)\s*\))?\s*",
            "count": r"\s*([+-]?\s*\d+(?:\.\d*)?)\s*-\s*([+-]?\s*\d+(?:\.\d*)?)(?:\s*\[(\d+(?:\.\d*)?)\s*\])?\s*"
        }
    }

    ################################################
    #
    # Initialization method from here.
    #
    ################################################

    def __init__(self, my_list, converter=None, allow_blank=True, exclude_list=None, run=True):
        self.my_list = my_list
        self.converter = converter
        self.allow_blank = allow_blank
        self.exclude_list = exclude_list
        self.re_bracket_start = None
        self.re_bracket_start_precheck = None
        self.re_bracket_end = None
        self.re_bracket_end_precheck = None
        self.re_range = None
        self.re_count = None
        self.compile_regex()
        if run:
            self.auto_normalize()

    def compile_regex(self):
        exclude_pattern = "|".join(self.exclude_list) if self.exclude_list else None
        if exclude_pattern is None:
            self.re_bracket_start = re.compile(r"^\[")
            self.re_bracket_end = re.compile(r"\]$")
        else:
            self.re_bracket_start = re.compile(fr"^\[(?!(?:{exclude_pattern})\])")
            self.re_bracket_end = re.compile(fr"(?<!\[(?:{exclude_pattern}))\]$")

        if self.converter not in self.numeric_pattern:
            return self
        # If the converter is either int or float.
        self.re_range = re.compile(self.numeric_pattern[self.converter]["range"])
        self.re_count = re.compile(self.numeric_pattern[self.converter]["count"])
        self.re_bracket_start_precheck = None
        self.re_bracket_end_precheck = self.re_count
        return self

    ################################################
    #
    # Public method from here.
    #
    ################################################

    ################################################
    # This method is executed at the time of initialization.
    #
    def auto_normalize(self):
        if not self.has_list_notation():
            self.numeric_range_parser()
            self.type_convert()
            return self
        else:
            self.fix_structure()
            self.numeric_range_parser()
            self.type_convert()
            self.fill_to_longest()
            return self

    def has_list_notation(self):
        return any(self._search_bracket(s) for s in self.my_list)

    def numeric_range_parser(self, my_list=None, depth=0):
        if self.converter not in self.numeric_pattern:
            return self

        my_list = self.my_list if my_list is None else my_list
        result = []
        is_matched = False
        for s in my_list:
            if isinstance(s, list):
                result.extend(self.numeric_range_parser(s, depth+1))
                continue

            match = self._numeric_range_to_list(s)
            if s != match:
                is_matched = True
                result.extend(match if not depth else [match])
                continue
            else:
                result.append(s)
                continue

        if depth:
            return self._transpose(result) if is_matched else [result]
        else:
            my_list[:] = result
            return self

    def type_convert(self, my_list=None):
        my_list = self.my_list if my_list is None else my_list
        for i, s in enumerate(my_list):
            if isinstance(s, list):
                self.type_convert(s)
            elif self.allow_blank and (str(s) in ["None", ""]):
                my_list[i] = None
            elif self.converter:
                my_list[i] = self.converter(s)
            else:
                my_list[i] = s
        return self

    def fix_structure(self):
        def is_same_length(list1, list2):
            return len(list1) == len(list2)

        start_indices, end_indices = [], []
        for i, s in enumerate(self.my_list):
            if is_same_length(start_indices, end_indices):
                replace_string = self._search_bracket(s, "[", replace="")
                if s != replace_string:
                    s = replace_string
                    start_indices.append(i)
            if not is_same_length(start_indices, end_indices):
                replace_string = self._search_bracket(s, "]", replace="")
                if s != replace_string:
                    s = replace_string
                    end_indices.append(i + 1)
            self.my_list[i] = s
        if not is_same_length(start_indices, end_indices):
            raise ValueError(f"Lengths of {start_indices} and {end_indices} are different.")
        # Restore the structure of a list.
        for i, j in zip(reversed(start_indices), reversed(end_indices)):
            self.my_list[i:j] = [self.my_list[i:j]]
        return self

    def fill_to_longest(self, my_list=None, value=None, index=None):
        my_list = self.my_list if my_list is None else my_list
        if not self.sublist_exists(my_list):
            return self
        max_length = max(len(sub_list) for sub_list in my_list if isinstance(sub_list, list))
        for i, sub_list in enumerate(my_list):
            if isinstance(sub_list, list):
                fill_value = value if index is None else sub_list[index]
                my_list[i] = sub_list + [fill_value] * (max_length-len(sub_list))
        return self

    def sublist_exists(self, my_list=None):
        my_list = self.my_list if my_list is None else my_list
        return any(isinstance(item, list) for item in my_list)

    def all_sublists(self, my_list=None):    # Unused method
        my_list = self.my_list if my_list is None else my_list
        return all(isinstance(item, list) for item in my_list)

    def get_list(self):                      # Unused method
        return self.my_list

    ################################################
    #
    # Private method from here.
    #
    ################################################

    def _search_bracket(self, string, bracket="[", replace=None):
        if bracket == "[":
            pattern = self.re_bracket_start
            precheck = self.re_bracket_start_precheck  # None
        elif bracket == "]":
            pattern = self.re_bracket_end
            precheck = self.re_bracket_end_precheck
        else:
            raise ValueError(f"Invalid argument provided. (bracket: {bracket})")

        if precheck and precheck.fullmatch(string):
            return None if replace is None else string
        elif replace is None:
            return pattern.search(string)
        else:
            return pattern.sub(replace, string)

    def _numeric_range_to_list(self, string):
        match = self.re_range.fullmatch(string)
        if match is not None:
            if self.converter == int:
                start = int(match.group(1))
                end = int(match.group(2)) + 1
                step = int(match.group(3)) if match.group(3) is not None else 1
                return list(range(start, end, step))
            else:              # float
                start = float(match.group(1))
                end = float(match.group(2))
                step = float(match.group(3)) if match.group(3) is not None else 1
                return np.arange(start, end + step, step).tolist()

        match = self.re_count.fullmatch(string)
        if match is not None:
            if self.converter == int:
                start = int(match.group(1))
                end = int(match.group(2))
                num = int(match.group(3)) if match.group(3) is not None else 1
                return [int(x) for x in np.linspace(start=start, stop=end, num=num).tolist()]
            else:              # float
                start = float(match.group(1))
                end = float(match.group(2))
                num = int(match.group(3)) if match.group(3) is not None else 1
                return np.linspace(start=start, stop=end, num=num).tolist()
        return string

    def _transpose(self, my_list=None):
        my_list = self.my_list if my_list is None else my_list
        my_list = [item if isinstance(item, list) else [item] for item in my_list]
        self.fill_to_longest(my_list, index=-1)
        return np.array(my_list, dtype=object).T.tolist()

    ################################################
    #
    # The methods of ListParser class end here.
    #
    ################################################


def find_dict(dict_list, keyword, search_key="name", stop=False):
    result = next((d for d in dict_list if d[search_key] == keyword), None)
    if result or not stop:
        return result
    else:
        raise ValueError(f"Dictionary with value '{keyword}' in key '{search_key}' not found.")


def choices_bool():
    return ["False", "True"]


def choices_model():
    update_cn_models()
    return list(cn_models_names.values())


def choices_control_mode():
    return [e.value for e in ControlMode]


def choices_resize_mode():
    return [e.value for e in ResizeMode]


def choices_preprocessor():
    return list(cn_preprocessor_modules)


def make_excluded_list():
    pattern = re.compile(r"\[(\w+)\]")
    return [match.group(1) for s in choices_model()
            for match in pattern.finditer(s)]

validation_data = [
        {"name": "model", "type": str, "check": choices_model, "exclude": make_excluded_list},
        {"name": "control_mode", "type": str, "check": choices_control_mode, "exclude": None},
        {"name": "resize_mode", "type": str, "check": choices_resize_mode, "exclude": None},
        {"name": "preprocessor", "type": str, "check": choices_preprocessor, "exclude": None},
    ]


def flatten(lst):
    result = []
    for element in lst:
        if isinstance(element, list):
            result.extend(flatten(element))
        else:
            result.append(element)
    return result


def is_all_included(target_list, check_list, allow_blank=False, stop=False):
    for element in flatten(target_list):
        if allow_blank and str(element) in ["None", ""]:
            continue
        elif element not in check_list:
            if not stop:
                return False
            else:
                raise ValueError(f"'{element}' is not included in check list.")
    return True


def bool_(string):
    string = str(string)
    if string in ["None", ""]:
        return None
    elif string.lower() in ["true", "1"]:
        return True
    elif string.lower() in ["false", "0"]:
        return False
    else:
        raise ValueError(f"Could not convert string to boolean: {string}")


def confirm(func_or_str):
    def confirm_(p, xs):
        if callable(func_or_str):
            # func_or_str is converter
            ListParser(xs, func_or_str, allow_blank=True)
            return
        elif isinstance(func_or_str, str):  # func_or_str is keyword
            valid_data = find_dict(validation_data, func_or_str, stop=True)
            converter = valid_data["type"]
            exclude_list = valid_data["exclude"]() if valid_data["exclude"] else None
            check_list = valid_data["check"]()
            ListParser(xs, converter, allow_blank=True, exclude_list=exclude_list)
            is_all_included(xs, check_list, allow_blank=True, stop=True)
            return
        else:
            raise TypeError(f"Argument must be callable or str, not {type(func_or_str).__name__}.")
    return confirm_


# class AxisOption:
#     def __init__(self, label, type, apply, format_value=format_value_add_label, confirm=None, cost=0.0, choices=None):
#         self.label = label
#         self.type = type
#         self.apply = apply
#         self.format_value = format_value
#         self.confirm = confirm
#         self.cost = cost
#         self.choices = choices
#
#
# class AxisOptionImg2Img(AxisOption):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.is_img2img = True
#
#
# class AxisOptionTxt2Img(AxisOption):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.is_img2img = False
from scripts.xyz_grid import AxisOption, AxisOptionTxt2Img, AxisOptionImg2Img

axis_options_aws = [
    AxisOption("Nothing", str, do_nothing, format_value=format_nothing),
    AxisOption("Seed", int, apply_field("seed")),
    AxisOption("Var. seed", int, apply_field("subseed")),
    AxisOption("Var. strength", float, apply_field("subseed_strength")),
    AxisOption("Steps", int, apply_field("steps")),
    AxisOptionTxt2Img("Hires steps", int, apply_field("hr_second_pass_steps")),
    AxisOption("CFG Scale", float, apply_field("cfg_scale")),
    AxisOptionImg2Img("Image CFG Scale", float, apply_field("image_cfg_scale")),
    AxisOption("Prompt S/R", str, apply_prompt, format_value=format_value),
    AxisOption("Prompt order", str_permutations, apply_order, format_value=format_value_join_list),
    AxisOptionTxt2Img("Sampler", str, apply_field("sampler_name"), format_value=format_value, confirm=confirm_samplers, choices=lambda: [x.name for x in sd_samplers.samplers if x.name not in opts.hide_samplers]),
    AxisOptionTxt2Img("Hires sampler", str, apply_field("hr_sampler_name"), confirm=confirm_samplers, choices=lambda: [x.name for x in sd_samplers.samplers_for_img2img if x.name not in opts.hide_samplers]),
    AxisOptionImg2Img("Sampler", str, apply_field("sampler_name"), format_value=format_value, confirm=confirm_samplers, choices=lambda: [x.name for x in sd_samplers.samplers_for_img2img if x.name not in opts.hide_samplers]),
    AxisOption("Checkpoint name", str, apply_checkpoint, format_value=format_remove_path, cost=1.0, choices=lambda: sorted(sd_models.checkpoints_list, key=str.casefold)),
    AxisOption("Negative Guidance minimum sigma", float, apply_field("s_min_uncond")),
    AxisOption("Sigma Churn", float, apply_field("s_churn")),
    AxisOption("Sigma min", float, apply_field("s_tmin")),
    AxisOption("Sigma max", float, apply_field("s_tmax")),
    AxisOption("Sigma noise", float, apply_field("s_noise")),
    AxisOption("Schedule type", str, apply_override("k_sched_type"), choices=lambda: list(sd_samplers_kdiffusion.k_diffusion_scheduler)),
    AxisOption("Schedule min sigma", float, apply_override("sigma_min")),
    AxisOption("Schedule max sigma", float, apply_override("sigma_max")),
    AxisOption("Schedule rho", float, apply_override("rho")),
    AxisOption("Eta", float, apply_field("eta")),
    AxisOption("Clip skip", int, apply_clip_skip),
    AxisOption("Denoising", float, apply_field("denoising_strength")),
    AxisOption("Initial noise multiplier", float, apply_field("initial_noise_multiplier")),
    AxisOption("Extra noise", float, apply_override("img2img_extra_noise")),
    AxisOptionTxt2Img("Hires upscaler", str, apply_field("hr_upscaler"), choices=lambda: [*shared.latent_upscale_modes, *[x.name for x in shared.sd_upscalers]]),
    AxisOptionImg2Img("Cond. Image Mask Weight", float, apply_field("inpainting_mask_weight")),
    AxisOption("VAE", str, apply_vae, cost=0.7, choices=lambda: ['None'] + list(sd_vae.vae_dict)),
    AxisOption("Styles", str, apply_styles, choices=lambda: list(shared.prompt_styles.styles)),
    AxisOption("UniPC Order", int, apply_uni_pc_order, cost=0.5),
    AxisOption("Face restore", str, apply_face_restore, format_value=format_value),
    AxisOption("Token merging ratio", float, apply_override('token_merging_ratio')),
    AxisOption("Token merging ratio high-res", float, apply_override('token_merging_ratio_hr')),
    AxisOption("Always discard next-to-last sigma", str, apply_override('always_discard_next_to_last_sigma', boolean=True), choices=boolean_choice(reverse=True)),
    AxisOption("SGM noise multiplier", str, apply_override('sgm_noise_multiplier', boolean=True), choices=boolean_choice(reverse=True)),
    AxisOption("Refiner checkpoint", str, apply_field('refiner_checkpoint'), format_value=format_remove_path, cost=1.0, choices=lambda: ['None'] + sorted(sd_models.checkpoints_list, key=str.casefold)),
    AxisOption("Refiner switch at", float, apply_field('refiner_switch_at')),
    AxisOption("RNG source", str, apply_override("randn_source"), choices=lambda: ["GPU", "CPU", "NV"]),

    AxisOption("[ControlNet] Enabled", identity, apply_field("control_net_enabled"), confirm=confirm(bool_), choices=choices_bool),
    AxisOption("[ControlNet] Model", identity, apply_field("control_net_model"), choices=choices_model, cost=0.9),
    AxisOption("[ControlNet] Weight", identity, apply_field("control_net_weight"), confirm=confirm(float)),
    AxisOption("[ControlNet] Guidance Start", identity, apply_field("control_net_guidance_start"), confirm=confirm(float)),
    AxisOption("[ControlNet] Guidance End", identity, apply_field("control_net_guidance_end"), confirm=confirm(float)),
    AxisOption("[ControlNet] Control Mode", identity, apply_field("control_net_control_mode"), confirm=confirm("control_mode"), choices=choices_control_mode),
    AxisOption("[ControlNet] Resize Mode", identity, apply_field("control_net_resize_mode"), confirm=confirm("resize_mode"), choices=choices_resize_mode),
    AxisOption("[ControlNet] Preprocessor", identity, apply_field("control_net_module"), confirm=confirm("preprocessor"), choices=choices_preprocessor),
    AxisOption("[ControlNet] Pre Resolution", identity, apply_field("control_net_pres"), confirm=confirm(int)),
    AxisOption("[ControlNet] Pre Threshold A", identity, apply_field("control_net_pthr_a"), confirm=confirm(float)),
    AxisOption("[ControlNet] Pre Threshold B", identity, apply_field("control_net_pthr_b"), confirm=confirm(float)),
]

shared.axis_options_aws = []

for x in axis_options_aws:
    if isinstance(x, AxisOption):
        shared.axis_options_aws.append(x)
    else:
        try:
            converted_obj = AxisOption(*x.__dict__)  # 使用实际参数来创建 AxisOption 对象
            shared.axis_options_aws.append(converted_obj)
        except Exception as e:
            print(f"Failed to convert object: {x}. Error: {e}")