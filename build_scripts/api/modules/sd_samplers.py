from modules import sd_samplers_compvis, sd_samplers_kdiffusion, shared

from diffusers import (
    DDPMScheduler,
    DDIMScheduler,
    PNDMScheduler,
    HeunDiscreteScheduler,
    LMSDiscreteScheduler,
    EulerDiscreteScheduler,
    EulerAncestralDiscreteScheduler,
    DPMSolverSinglestepScheduler,
    DPMSolverMultistepScheduler,
    KDPM2DiscreteScheduler,
    KDPM2AncestralDiscreteScheduler,
)

# imports for functions that previously were here and are used by other modules
from modules.sd_samplers_common import samples_to_image_grid, sample_to_image  # noqa: F401

all_samplers = [
    *sd_samplers_kdiffusion.samplers_data_k_diffusion,
    *sd_samplers_compvis.samplers_data_compvis,
]
all_samplers_map = {x.name: x for x in all_samplers}

samplers = []
samplers_for_img2img = []
samplers_map = {}


def find_sampler_config(name):
    if name is not None:
        config = all_samplers_map.get(name, None)
    else:
        config = all_samplers[0]

    return config


def create_sampler(name, model):
    config = find_sampler_config(name)

    assert config is not None, f'bad sampler name: {name}'

    if model.is_sdxl and config.options.get("no_sdxl", False):
        raise Exception(f"Sampler {config.name} is not supported for SDXL")

    sampler = config.constructor(model)
    sampler.config = config

    return sampler


def set_samplers():
    global samplers, samplers_for_img2img

    hidden = set(shared.opts.hide_samplers)
    hidden_img2img = set(shared.opts.hide_samplers + ['PLMS', 'UniPC'])

    samplers = [x for x in all_samplers if x.name not in hidden]
    samplers_for_img2img = [x for x in all_samplers if x.name not in hidden_img2img]

    samplers_map.clear()
    for sampler in all_samplers:
        samplers_map[sampler.name.lower()] = sampler.name
        for alias in sampler.aliases:
            samplers_map[alias.lower()] = sampler.name

def update_sampler(name, pipeline, pipeline_name):

    # #TODO check compatibility
    # check_comp(name, pipeline)
    # https://huggingface.co/docs/diffusers/api/schedulers/overview

    if name == 'Euler a':
        pipeline.scheduler = EulerAncestralDiscreteScheduler.from_config(pipeline.scheduler.config)
    elif name == 'Euler':
        pipeline.scheduler = EulerDiscreteScheduler.from_config(pipeline.scheduler.config)
    elif name == 'LMS':
        pipeline.scheduler = LMSDiscreteScheduler.from_config(pipeline.scheduler.config)
    elif name == 'Heun':
        pipeline.scheduler = HeunDiscreteScheduler.from_config(pipeline.scheduler.config)
    elif name == 'DPM2':
        pipeline.scheduler = DPMSolverMultistepScheduler.from_config(pipeline.scheduler.config)
    elif name == 'DPM2 a':
        pipeline.scheduler = DPMSolverMultistepScheduler.from_config(pipeline.scheduler.config, use_karra_sigma=True)
    elif name == 'DPM++ 2S a':
        raise NotImplementedError
    elif name == 'DPM++ 2M':
        pipeline.scheduler = DPMSolverMultistepScheduler.from_config(pipeline.scheduler.config)
    elif name == 'DPM++ SDE':
        pipeline.scheduler = DPMSolverSinglestepScheduler.form_config(pipeline.scheduler.config)
    elif name == 'DPM++ 2M SDE':
        pipeline.scheduler = DPMSolverMultistepScheduler.from_config(pipeline.scheduler.config, algorithm_type="sde-dpmsolver++")
    elif name == 'DPM fast':
        raise NotImplementedError
    elif name == 'DPM adaptive':
        raise NotImplementedError
    elif name == 'LMS Karras':
        pipeline.scheduler = LMSDiscreteScheduler.from_config(pipeline.scheduler.config, use_karras_sigma=True)
    elif name == 'DPM2 Karras':
        pipeline.scheduler = KDPM2DiscreteScheduler.from_config(pipeline.scheduler.config, use_karras_sigma=True)
    elif name == 'DPM2 a Karras':
        pipeline.scheduler = KDPM2AncestralDiscreteScheduler.from_config(pipeline.scheduler.config, use_karras_sigma=True)
    elif name == 'DPM++ 2S a Karras':
        raise NotImplementedError
    elif name == 'DPM++ 2M Karras':
        pipeline.scheduler = DPMSolverMultistepScheduler.from_config(pipeline.scheduler.config, use_karras_sigma=True)
    elif name == 'DPM++ SDE Karras':
        pipeline.scheduler = DPMSolverSinglestepScheduler.from_config(pipeline.scheduler.config, use_karras_sigma=True)
    elif name == 'DPM++ 2M SDE Karras':
        pipeline.scheduler = DPMSolverMultistepScheduler.from_config(pipeline.scheduler.config, use_karras_sigma=True, algorithm_type="sde-dpmsolver++")
    else:
        raise NotImplementedError

    return pipeline

set_samplers()
