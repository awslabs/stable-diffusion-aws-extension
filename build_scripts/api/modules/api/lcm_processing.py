from modules import shared
from modules.api import models
from diffusers import DiffusionPipeline, UNet2DConditionModel, LCMScheduler
from PIL import Image
import torch
from modules.api.mme_utils import encode_pil_to_base64, decode_base64_to_image
from fastapi.exceptions import HTTPException


def lcm_pipeline(payload, used_models):
    sd_model_name = used_models['Stable-diffusion'][0]
    init_images = None
    mask = None
    seed = payload['seed']
    generator = torch.manual_seed(seed)
    if 'init_images' in payload.keys():
        init_images = payload['init_images']
    if 'mask' in payload.keys():
        mask = payload['mask']

    if 'sdxl' in sd_model_name:
        if 'lcm_sdxl' not in shared.sd_pipeline.pipeline_name:
            unet = UNet2DConditionModel.from_pretrained("latent-consistency/lcm-sdxl", torch_dtype=torch.float16, variant="fp16")
        
        if init_images is not None and mask is not None:
            if shared.sd_pipeline.pipeline_name != 'lcm_sdxl_inpaint':
                shared.sd_pipeline = DiffusionPipeline.from_pretrained("diffusers/stable-diffusion-xl-1.0-inpainting-0.1", unet=unet, torch_dtype=torch.float16, variant="fp16")
                shared.sd_pipeline.pipeline_name = 'lcm_sdxl_inpaint'
                shared.opts.data["sd_model_checkpoint_path"] = 'lcm_sdxl_inpaint'
        else:
            if shared.sd_pipeline.pipeline_name != 'lcm_sdxl':            
                shared.sd_pipeline = DiffusionPipeline.from_pretrained("stabilityai/stable-diffusion-xl-base-1.0", unet=unet, torch_dtype=torch.float16, variant="fp16")
                shared.sd_pipeline.pipeline_name = 'lcm_sdxl'
                shared.opts.data["sd_model_checkpoint_path"] = 'lcm_sdxl'
        shared.sd_pipeline.scheduler = LCMScheduler.from_config(shared.sd_pipeline.scheduler.config)      
    else:
        if shared.sd_pipeline.pipeline_name != 'lcm_sdv15':
            shared.sd_pipeline = DiffusionPipeline.from_pretrained("SimianLuo/LCM_Dreamshaper_v7", custom_pipeline="latent_consistency_txt2img", torch_dtype=torch.float16, variant="fp16")
            shared.sd_pipeline.pipeline_name = 'lcm_sdv15'
            shared.opts.data["sd_model_checkpoint_path"] = 'lcm_sdv15'
    shared.sd_pipeline.generator = generator
    shared.sd_pipeline.to('cuda')
    if init_images is not None and mask is not None:
        input_images = [decode_base64_to_image(x) for x in init_images]
        mask = decode_base64_to_image(mask)
        output = shared.sd_pipeline(prompt=payload['prompt'], 
                                    image=input_images,
                                    mask=mask, 
                                    strength=payload['strength'], 
                                    negative_prompt=payload['negative_prompt'],
                                    height=payload['height'],
                                    width=payload['width'],
                                    guidance_scale=payload['cfg_scale'],
                                    num_inference_steps=payload['steps']).images
    elif init_images is not None:
        input_images = [decode_base64_to_image(x) for x in init_images]
        output = shared.sd_pipeline(prompt=payload['prompt'], 
                                    image=input_images,
                                    strength=payload['strength'], 
                                    negative_prompt=payload['negative_prompt'],
                                    height=payload['height'],
                                    width=payload['width'],
                                    guidance_scale=payload['cfg_scale'],
                                    num_inference_steps=payload['steps']).images
    else:   
        output = shared.sd_pipeline(
                prompt=payload['prompt'],
                negative_prompt=payload['negative_prompt'],
                height=payload['height'],
                width=payload['width'],
                guidance_scale=payload['cfg_scale'],
                num_inference_steps=payload['steps']
                ).images
    b64images = list(map(encode_pil_to_base64, output))
    generate_parameter={}
    generate_parameter['prompt'] = payload['prompt']
    generate_parameter['negative_prompt'] = payload['negative_prompt']
    generate_parameter['seed'] = payload['seed']
    generate_parameter['cfg_scale'] = payload['cfg_scale']
    generate_parameter['steps'] = payload['steps']
  

    return models.TextToImageResponse(images=b64images, parameters=generate_parameter)


def lcm_lora_pipeline(payload, used_models):
    sd_model_name = used_models['Stable-diffusion'][0]
    controlnet_model = None
    if 'ControlNet' in used_models:
        controlnet_models = used_models['ControlNet']
    
    init_images = None
    mask = None
    control_images = None 
    seed = payload['seed']
    generator = torch.manual_seed(seed)
    if 'init_images' in payload:
        init_images = payload['init_images']
    if 'mask' in payload:
        mask = payload['mask']
    if 'control_image' in payload.keys():
        control_images = payload['control_image']    

    if 'sdxl' in sd_model_name:
        if shared.sd_pipeline.pipeline_name != 'lcm_sdxl':
            unet = UNet2DConditionModel.from_pretrained("latent-consistency/lcm-sdxl", torch_dtype=torch.float16, variant="fp16")
            shared.sd_pipeline = DiffusionPipeline.from_pretrained("stabilityai/stable-diffusion-xl-base-1.0", unet=unet, torch_dtype=torch.float16, variant="fp16")
            shared.sd_pipeline.scheduler = LCMScheduler.from_config(shared.sd_pipeline.scheduler.config)
            shared.sd_pipeline.pipeline_name = 'lcm_lora_sdxl'
            shared.opts.data["sd_model_checkpoint_path"] = 'lcm_lora_sdxl'
    else:
        if shared.sd_pipeline.pipeline_name != 'lcm_loral_sdv15':
            shared.sd_pipeline = DiffusionPipeline.from_pretrained("SimianLuo/LCM_Dreamshaper_v7", custom_pipeline="latent_consistency_txt2img", torch_dtype=torch.float16, variant="fp16")
            shared.sd_pipeline.pipeline_name = 'lcm_loral_sdv15'
            shared.opts.data["sd_model_checkpoint_path"] = 'lcm_lora_sdv15'
    
    shared.sd_pipeline.to('cuda')
    input_images = [decode_base64_to_image(x) for x in init_images]
    output = shared.sd_pipeline(
                prompt=payload['prompt'],
                negative_prompt=payload['negative_prompt'],
                height=payload['height'],
                width=payload['width'],
                guidance_scale=payload['cfg_scale'],
                num_inference_steps=payload['steps']
                ).images
    b64images = list(map(encode_pil_to_base64, output))

    generate_parameter={}
    generate_parameter['prompt'] = payload['prompt']
    generate_parameter['negative_prompt'] = payload['negative_prompt']
    generate_parameter['seed'] = payload['seed']
    generate_parameter['cfg_scale'] = payload['cfg_scale']
    generate_parameter['steps'] = payload['steps']

    return models.TextToImageResponse(images=b64images, parameters=generate_parameter)