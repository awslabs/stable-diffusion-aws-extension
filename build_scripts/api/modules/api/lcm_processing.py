from modules import shared
from modules.api import models
from diffusers import DiffusionPipeline, UNet2DConditionModel, LCMScheduler, StableDiffusionXLControlNetPipeline, StableDiffusionControlNetPipeline, StableDiffusionInpaintPipeline
import torch
from modules.api.mme_utils import encode_pil_to_base64, decode_base64_to_image
from diffusers import AutoPipelineForInpainting, AutoPipelineForText2Image, AutoPipelineForImage2Image, ControlNetModel, StableDiffusionXLPipeline, StableDiffusionPipeline
from diffusers.pipelines.controlnet import MultiControlNetModel
from diffusers import StableDiffusionXLControlNetInpaintPipeline, StableDiffusionControlNetInpaintPipeline
from modules.paths_internal import models_path
import os
import random

sd_model_folder = "Stable-diffusion"
controlnet_folder = 'ControlNet'
sd_model_path = os.path.abspath(os.path.join(models_path, sd_model_folder))
controlnet_path = os.path.abspath(os.path.join(models_path, sd_model_folder))

def lcm_pipeline(payload, used_models):
    sd_model_name = used_models['Stable-diffusion'][0]['model_name']
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
                                    mask_image=mask, 
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
  

    return models.TextToImageResponse(images=b64images, parameters=generate_parameter, info='')


def lcm_lora_pipeline(payload, used_models):
    sd_model_name = used_models['Stable-diffusion'][0]['model_name']
    controlnet_models = None
    if 'ControlNet' in used_models:
        controlnet_models = used_models['ControlNet']
    
    init_images = None
    mask = None
    control_images = None
    strength = 1 
    if 'seed' in payload:
        seed = payload['seed']
    else:
        seed = -1

    if seed == -1:
        seed = int(random.randrange(4294967294))

    generator = torch.manual_seed(seed)
    if 'init_images' in payload:
        init_images = payload['init_images']
        init_images = [decode_base64_to_image(x) for x in init_images]
    if 'mask' in payload:
        mask = payload['mask']
        mask = decode_base64_to_image(mask)
    if 'control_image' in payload:
        control_images = payload['control_image'] 
        input_control_imgs =  [decode_base64_to_image(x) for x in control_images]
    if 'strength' in payload:
        strength = payload['strength']
    
    if 'xl' in sd_model_name and 'inpainting' in sd_model_name:
        if shared.sd_pipeline.pipeline_name != 'LCM_Lora_SDXL_Inpaint':
            shared.sd_pipeline.to('cpu')
            shared.sd_pipeline = DiffusionPipeline.from_pretrained(sd_model_name, torch_dtype=torch.float16, load_safety_checker=False, variant="fp16").to('cuda')
            shared.sd_pipeline.pipeline_name = 'LCM_Lora_SDXL_Inpaint'
            shared.opts.data["sd_checkpoint_name"] = os.path.splitext(sd_model_name)[0]
            shared.sd_pipeline.load_lora_weights("latent-consistency/lcm-lora-sdxl")
    elif 'xl' in sd_model_name:
        if shared.opts.data["sd_checkpoint_name"] != os.path.splitext(sd_model_name)[0]:
            shared.sd_pipeline.to('cpu')
            shared.sd_pipeline = StableDiffusionXLPipeline.from_single_file(os.path.join(sd_model_path, sd_model_name), torch_dtype=torch.float16, load_safety_checker=False, variant="fp16").to('cuda')
            shared.opts.data["sd_checkpoint_name"] = os.path.splitext(sd_model_name)[0]
        if shared.sd_pipeline.pipeline_name != 'LCM_Lora_SDXL':
            shared.sd_pipeline.unload_lora_weights()
            shared.sd_pipeline.load_lora_weights("latent-consistency/lcm-lora-sdxl")
            shared.sd_pipeline.pipeline_name = 'LCM_Lora_SDXL'
    else:
        if 'inpainting' in sd_model_name:
            if shared.opts.data["sd_checkpoint_name"] != os.path.splitext(sd_model_name)[0]:
                shared.sd_pipeline.to('cpu')
                shared.sd_pipeline = StableDiffusionInpaintPipeline.from_single_file(os.path.join(sd_model_path, sd_model_name), torch_dtype=torch.float16, load_safety_checker=False, variant="fp16").to('cuda')
                shared.opts.data["sd_checkpoint_name"] = os.path.splitext(sd_model_name)[0]
            if shared.sd_pipeline.pipeline_name != 'LCM_Lora_SD15_Inpaint':
                shared.sd_pipeline.unload_lora_weights()
                shared.sd_pipeline.pipeline_name = 'LCM_Lora_SD15_Inpaint'
                shared.sd_pipeline.load_lora_weights("latent-consistency/lcm-lora-sdv1-5")
        else:
            if shared.opts.data["sd_checkpoint_name"] != os.path.splitext(sd_model_name)[0]:
                shared.sd_pipeline.to('cpu')
                shared.sd_pipeline = StableDiffusionPipeline.from_single_file(os.path.join(sd_model_path, sd_model_name), torch_dtype=torch.float16, load_safety_checker=False, variant="fp16").to('cuda')
                shared.opts.data["sd_checkpoint_name"] = os.path.splitext(sd_model_name)[0]
            if shared.sd_pipeline.pipeline_name != 'LCM_Lora_SD15':
                shared.sd_pipeline.unload_lora_weights()
                shared.sd_pipeline.load_lora_weights("latent-consistency/lcm-lora-sdv1-5")
                shared.sd_pipeline.pipeline_name = 'LCM_Lora_SD15'

    if init_images is not None and mask is None:
        shared.sd_pipeline = AutoPipelineForImage2Image(**shared.sd_pipeline.components)
    
    valid_controlnets = []
    if controlnet_models is not None:
        for controlnet_model in controlnet_models:
            network = ControlNetModel.from_pretrained(controlnet_model)
            network.to(shared.sd_pipeline.device, dtype=shared.sd_pipeline.vae.dtype)
            valid_controlnets.append(network)
        if len(valid_controlnets) == 1:
            valid_control_networks = valid_controlnets[0]
        elif len(valid_controlnets) > 1:
            valid_control_networks = MultiControlNetModel(valid_controlnets)
        if 'XL' in shared.sd_pipeline.pipeline_name:
            pipeline_class = StableDiffusionXLControlNetPipeline
            if 'inpainting' in shared.sd_pipeline.pipeline_name:
                pipeline_class = StableDiffusionXLControlNetInpaintPipeline
            if 'controlnet' in list(shared.sd_pipeline.components.keys()):
                shared.sd_pipeline = pipeline_class(**shared.sd_pipeline.components)
                shared.sd_pipeline.controlnet = valid_control_networks
            else:
                shared.sd_pipeline = pipeline_class(**shared.sd_pipeline.components, controlnet=valid_control_networks)
            shared.sd_pipeline_pipeline_name = 'LCM_SDXL_Controlnet'
        else:
            pipeline_class = StableDiffusionControlNetPipeline
            if 'inpainting' in shared.sd_pipeline.pipeline_name:
                pipeline_class = StableDiffusionControlNetInpaintPipeline
            if 'controlnet' in list(shared.sd_pipeline.components.keys()):
                shared.sd_pipeline = pipeline_class(**shared.sd_pipeline.components)
                shared.sd_pipeline.controlnet = valid_control_networks
            else:
                shared.sd_pipeline = pipeline_class(**shared.sd_pipeline.components, controlnet=valid_control_networks)
            shared.sd_pipeline_pipeline_name = 'LCM_SD_Controlnet'
    elif 'controlnet' in list(shared.sd_pipeline.components.keys()):
        if init_images is not None and mask is not None:
            if 'xl' in sd_model_name:
                shared.sd_pipeline = AutoPipelineForInpainting(vae=shared.sd_pipeline.vae, text_encoder_2=shared.sd_pipeline.text_encoder_2, text_encoder=shared.sd_pipeline.text_encoder, tokenizer=shared.sd_pipeline.tokenizer, tokenizer_2=shared.sd_pipeline.tokenizer_2, unet=shared.sd_pipeline.unet, scheduler=shared.sd_pipeline.scheduler)
            else:
                shared.sd_pipeline = AutoPipelineForInpainting(vae=shared.sd_pipeline.vae, text_encoder=shared.sd_pipeline.text_encoder, tokenizer=shared.sd_pipeline.tokenizer, unet=shared.sd_pipeline.unet, scheduler=shared.sd_pipeline.scheduler)    
        elif init_images is not None:
            if 'xl' in sd_model_name:
                shared.sd_pipeline = AutoPipelineForImage2Image(vae=shared.sd_pipeline.vae, text_encoder_2=shared.sd_pipeline.text_encoder_2, text_encoder=shared.sd_pipeline.text_encoder, tokenizer=shared.sd_pipeline.tokenizer, tokenizer_2=shared.sd_pipeline.tokenizer_2, unet=shared.sd_pipeline.unet, scheduler=shared.sd_pipeline.scheduler)
            else:
                shared.sd_pipeline = AutoPipelineForImage2Image(vae=shared.sd_pipeline.vae, text_encoder=shared.sd_pipeline.text_encoder, tokenizer=shared.sd_pipeline.tokenizer, unet=shared.sd_pipeline.unet, scheduler=shared.sd_pipeline.scheduler)    
        else:
            if 'xl' in sd_model_name:
                shared.sd_pipeline = AutoPipelineForText2Image(vae=shared.sd_pipeline.vae, text_encoder_2=shared.sd_pipeline.text_encoder_2, text_encoder=shared.sd_pipeline.text_encoder, tokenizer=shared.sd_pipeline.tokenizer, tokenizer_2=shared.sd_pipeline.tokenizer_2, unet=shared.sd_pipeline.unet, scheduler=shared.sd_pipeline.scheduler)
            else:
                shared.sd_pipeline = AutoPipelineForText2Image(vae=shared.sd_pipeline.vae, text_encoder=shared.sd_pipeline.text_encoder, tokenizer=shared.sd_pipeline.tokenizer, unet=shared.sd_pipeline.unet, scheduler=shared.sd_pipeline.scheduler)    

    shared.sd_pipeline.scheduler = LCMScheduler.from_config(shared.sd_pipeline.scheduler.config)
    
    if 'controlnet' in shared.sd_pipeline.pipeline_name:
        output = shared.sd_pipeline(
                    prompt=payload['prompt'],
                    negative_prompt=payload['negative_prompt'],
                    height=payload['height'],
                    width=payload['width'],
                    image=input_control_imgs,
                    controlnet_conditioning_scale=payload['controlnet_conditioning_scale'],
                    guidance_scale=payload['cfg_scale'],
                    num_inference_steps=payload['steps'],
                    generator=generator
                    ).images
    else:
        # output = shared.sd_pipeline(
        #             prompt='a beautiful girl of realistic style',
        #             negative_prompt=payload['negative_prompt'],
        #             height=payload['height'],
        #             width=payload['width'],
        #             guidance_scale=payload['cfg_scale'],
        #             num_inference_steps=payload['steps'],
        #             generator=generator
        #             ).images
        output = shared.sd_pipeline(
                    prompt=payload['prompt'],
                    negative_prompt=payload['negative_prompt'],
                    height=payload['height'],
                    width=payload['width'],
                    image=init_images,
                    mask_image=mask,
                    strength=strength,
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

    return models.TextToImageResponse(images=b64images, parameters=generate_parameter, info='')