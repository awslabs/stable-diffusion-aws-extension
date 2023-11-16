import json
import logging
import math
import os
import sys
import hashlib

import torch
import numpy as np
from PIL import Image, ImageOps
import random
import cv2
from skimage import exposure
from typing import Any

from modules import devices, prompt_parser, masking, sd_samplers, lowvram, extra_networks
from modules.shared import opts
import modules.shared as shared
import modules.images as images
import modules.styles
# some of those options should not be changed at all because they would break the model, so I removed them from options.

from diffusers import StableDiffusionControlNetPipeline, StableDiffusionXLControlNetPipeline, StableDiffusionControlNetImg2ImgPipeline, StableDiffusionControlNetInpaintPipeline, StableDiffusionXLControlNetImg2ImgPipeline, StableDiffusionXLControlNetInpaintPipeline
from diffusers import StableDiffusionPipeline, StableDiffusionXLPipeline, StableDiffusionImg2ImgPipeline, StableDiffusionInpaintPipeline, StableDiffusionXLImg2ImgPipeline, StableDiffusionXLInpaintPipeline
from modules.custome_pipeline.stable_diffusion_controlnet_reference import StableDiffusionControlNetReferencePipeline
from modules.custome_pipeline.stable_diffusion_reference import StableDiffusionReferencePipeline
from modules.custome_pipeline.stable_diffusion_xl_reference import StableDiffusionXLReferencePipeline
from diffusers.pipelines.controlnet import MultiControlNetModel

def convert_pipeline(controlnet_state, controlnet_script, request_type, extra_generation_params, image_mask=None):
    controlnet_images = None
    ref_image = None
    inpaint_image = None
    pipeline_name = shared.sd_pipeline.pipeline_name
    
    if controlnet_state == True:
        # TODO XY: update pipeline
        # get controled image
        
        controlnet_images = []
        idx = 0
        reference_only = False
        inpaint_type = False
        log_keys = list(extra_generation_params.keys())
        valid_controlnets = []
        for detected_map in controlnet_script.detected_map:
            log_key = log_keys[idx]
            preprocessor = extra_generation_params[log_key]
            controlnet_model = controlnet_script.control_networks[idx]
            idx += 1
            if 'reference' in preprocessor:
                ref_image = Image.fromarray(detected_map[0])
                reference_only = True
            if 'inpaint' in preprocessor:
                 inpaint_image = Image.fromarray(detected_map[0])
                 inpaint_type = True
            else:
                controlnet_image = detected_map[0]
                controlnet_images.append(Image.fromarray(controlnet_image.astype(np.uint8)))
                valid_controlnets.append(controlnet_model)
        
        if len(valid_controlnets) == 1:
            valid_control_networks = valid_controlnets[0]
        elif len(valid_controlnets) > 1:
            valid_control_networks = MultiControlNetModel(valid_controlnets)
        
        #'sd-v1-5-inpainting.ckpt'
        # diffusers/stable-diffusion-xl-1.0-inpainting-0.1

        if request_type == 'StableDiffusionPipelineTxt2Img':
            if 'XL' in pipeline_name:
                if reference_only and len(controlnet_images) == 0:
                    shared.sd_pipeline = StableDiffusionXLReferencePipeline(**shared.sd_pipeline.components)
                    shared.sd_pipeline.pipeline_name = 'StableDiffusionXLReferencePipeline'
                elif inpaint_type and len(controlnet_images) == 0:
                    shared.sd_pipeline = StableDiffusionXLInpaintPipeline(**shared.sd_pipeline.components)
                    shared.sd_pipeline.pipeline_name = 'StableDiffusionXLInpaintPipeline'
                    #load xlinpaint model and change the unet model
                    xl_inpaint_pipeline = StableDiffusionXLInpaintPipeline.from_pretrain('diffusers/stable-diffusion-xl-1.0-inpainting-0.1', torch_dtype=torch.float16).to('cuda')
                    shared.sd_pipeline.unet = xl_inpaint_pipeline.unet
                elif inpaint_type:
                    if 'controlnet' in list(shared.sd_pipeline.components.keys()):
                        shared.sd_pipeline = StableDiffusionXLControlNetInpaintPipeline(**shared.sd_pipeline.components)
                        shared.sd_pipeline.controlnet = valid_control_networks
                    else:
                        shared.sd_pipeline = StableDiffusionXLControlNetInpaintPipeline(**shared.sd_pipeline.components, controlnet=valid_control_networks)
                    shared.sd_pipeline.pipeline_name = 'StableDiffusionXLControlNetInpaintPipeline'
                else:
                    if 'controlnet' in list(shared.sd_pipeline.components.keys()):
                        shared.sd_pipeline = StableDiffusionXLControlNetPipeline(**shared.sd_pipeline.components)
                        shared.sd_pipeline.controlnet = valid_control_networks
                    else:
                        shared.sd_pipeline = StableDiffusionXLControlNetPipeline(**shared.sd_pipeline.components, controlnet=valid_control_networks)
                    shared.sd_pipeline.pipeline_name = 'StableDiffusionXLControlNetPipeline'
            else:
                if reference_only and len(controlnet_images) > 0:
                    if 'controlnet' in list(shared.sd_pipeline.components.keys()):
                        shared.sd_pipeline = StableDiffusionControlNetReferencePipeline(**shared.sd_pipeline.components)
                        shared.sd_pipeline.controlnet = valid_control_networks
                    else:
                        shared.sd_pipeline = StableDiffusionControlNetReferencePipeline(**shared.sd_pipeline.components, controlnet=valid_control_networks)
                    shared.sd_pipeline.pipeline_name = 'StableDiffusionControlNetReferencePipeline'
                elif reference_only:
                    shared.sd_pipeline = StableDiffusionReferencePipeline(**shared.sd_pipeline.components)
                    shared.sd_pipeline.pipeline_name = 'StableDiffusionReferencePipeline'
                elif inpaint_type and len(controlnet_images) == 0:
                    shared.sd_pipeline = StableDiffusionInpaintPipeline(**shared.sd_pipeline.components)
                    #load inpaint model and change the unet model
                    if shared.sd_pipeline.pipeline_name != 'StableDiffusionInpaintPipeline' and shared.sd_pipeline.pipeline_name != 'StableDiffusionControlNetInpaintPipeline' and shared.opts.data["sd_checkpoint_name"] != 'sd-v1-5-inpainting':
                        inpaint_pipeline = StableDiffusionInpaintPipeline.from_pretrain('runwayml/stable-diffusion-inpainting', torch_dtype=torch.float16).to('cuda')
                        shared.sd_pipeline.unet = inpaint_pipeline.unet
                    shared.sd_pipeline.pipeline_name = 'StableDiffusionInpaintPipeline'
                elif inpaint_type:
                    if 'controlnet' in list(shared.sd_pipeline.components.keys()):
                        shared.sd_pipeline = StableDiffusionControlNetInpaintPipeline(**shared.sd_pipeline.components)
                        shared.sd_pipeline.controlnet = valid_control_networks
                    else:
                        shared.sd_pipeline = StableDiffusionControlNetInpaintPipeline(**shared.sd_pipeline.components, controlnet=valid_control_networks)
                    if shared.sd_pipeline.pipeline_name != 'StableDiffusionInpaintPipeline' and shared.sd_pipeline.pipeline_name != 'StableDiffusionControlNetInpaintPipeline' and shared.opts.data["sd_checkpoint_name"] != 'sd-v1-5-inpainting':
                        inpaint_pipeline = StableDiffusionInpaintPipeline.from_pretrain('runwayml/stable-diffusion-inpainting', torch_dtype=torch.float16).to('cuda')
                        shared.sd_pipeline.unet = inpaint_pipeline.unet
                    shared.sd_pipeline.pipeline_name = 'StableDiffusionControlNetInpaintPipeline'
                else:
                    if 'controlnet' in list(shared.sd_pipeline.components.keys()):
                        shared.sd_pipeline = StableDiffusionControlNetPipeline(**shared.sd_pipeline.components)
                        shared.sd_pipeline.controlnet = valid_control_networks                            
                    else:
                        shared.sd_pipeline = StableDiffusionControlNetPipeline(**shared.sd_pipeline.components, controlnet=valid_control_networks)
                    shared.sd_pipeline.pipeline_name = 'StableDiffusionControlNetPipeline'
        
        elif request_type == 'StableDiffusionPipelineImg2Img':  
            if 'XL' in pipeline_name:
                if image_mask is None:
                    if 'controlnet' in list(shared.sd_pipeline.components.keys()):
                        shared.sd_pipeline = StableDiffusionXLControlNetImg2ImgPipeline(**shared.sd_pipeline.components)
                        shared.sd_pipeline.controlnet = valid_control_networks
                    else:
                        shared.sd_pipeline = StableDiffusionXLControlNetImg2ImgPipeline(**shared.sd_pipeline.components, controlnet=valid_control_networks)
                    shared.sd_pipeline.pipeline_name = 'StableDiffusionXLControlNetImg2ImgPipeline'
                else:
                    if 'controlnet' in list(shared.sd_pipeline.components.keys()):
                        shared.sd_pipeline = StableDiffusionXLControlNetInpaintPipeline(**shared.sd_pipeline.components)
                        shared.sd_pipeline.controlnet = valid_control_networks
                    else:
                        shared.sd_pipeline = StableDiffusionXLControlNetInpaintPipeline(**shared.sd_pipeline.components, controlnet=valid_control_networks)
                    shared.sd_pipeline.pipeline_name = 'StableDiffusionXLControlNetInpaintPipeline'
            else:
                if image_mask is None:
                    if 'controlnet' in list(shared.sd_pipeline.components.keys()):
                        shared.sd_pipeline = StableDiffusionControlNetImg2ImgPipeline(**shared.sd_pipeline.components)
                        shared.sd_pipeline.controlnet = valid_control_networks
                    else:
                        shared.sd_pipeline = StableDiffusionControlNetImg2ImgPipeline(**shared.sd_pipeline.components, controlnet = valid_control_networks)
                    shared.sd_pipeline.pipeline_name = 'StableDiffusionControlNetImg2ImgPipeline'
                else:
                    if 'controlnet' in list(shared.sd_pipeline.components.keys()):
                        shared.sd_pipeline = StableDiffusionControlNetInpaintPipeline(**shared.sd_pipeline.components)
                        shared.sd_pipeline.controlnet = valid_control_networks
                    else:
                        shared.sd_pipeline = StableDiffusionControlNetInpaintPipeline(**shared.sd_pipeline.components, controlnet = valid_control_networks)
                    if shared.sd_pipeline.pipeline_name != 'StableDiffusionInpaintPipeline' and shared.sd_pipeline.pipeline_name != 'StableDiffusionControlNetInpaintPipeline':
                        inpaint_pipeline = StableDiffusionInpaintPipeline.from_pretrain('runwayml/stable-diffusion-inpainting', torch_dtype=torch.float16).to('cuda')
                        shared.sd_pipeline.unet = inpaint_pipeline.unet
                    shared.sd_pipeline.pipeline_name = 'StableDiffusionControlNetInpaintPipeline'
    else:
        if request_type == 'StableDiffusionPipelineTxt2Img':
            if 'XL' in pipeline_name:
                #shared.sd_pipeline = StableDiffusionXLPipeline(**shared.sd_pipeline.components)
                shared.sd_pipeline = StableDiffusionXLPipeline(vae=shared.sd_pipeline.vae, text_encoder_2=shared.sd_pipeline.text_encoder_2, text_encoder=shared.sd_pipeline.text_encoder, tokenizer=shared.sd_pipeline.tokenizer, tokenizer_2=shared.sd_pipeline.tokenizer_2, unet=shared.sd_pipeline.unet, scheduler=shared.sd_pipeline.scheduler)
                shared.sd_pipeline.pipeline_name = 'StableDiffusionXLPipeline'
            else:
                #shared.sd_pipeline = StableDiffusionPipeline(**shared.sd_pipeline.components)
                shared.sd_pipeline = StableDiffusionPipeline(vae=shared.sd_pipeline.vae, text_encoder=shared.sd_pipeline.text_encoder, tokenizer=shared.sd_pipeline.tokenizer, unet=shared.sd_pipeline.unet, scheduler=shared.sd_pipeline.scheduler, safety_checker=shared.sd_pipeline.safety_checker, feature_extractor=shared.sd_pipeline.feature_extractor)
                shared.sd_pipeline.pipeline_name = 'StableDiffusionPipeline'
        elif request_type == 'StableDiffusionPipelineImg2Img':  
            if 'XL' in pipeline_name:
                if image_mask is None:
                    #shared.sd_pipeline = StableDiffusionXLImg2ImgPipeline(**shared.sd_pipeline.components)
                    shared.sd_pipeline = StableDiffusionXLImg2ImgPipeline(vae=shared.sd_pipeline.vae, text_encoder_2=shared.sd_pipeline.text_encoder_2, text_encoder=shared.sd_pipeline.text_encoder, tokenizer=shared.sd_pipeline.tokenizer, tokenizer_2=shared.sd_pipeline.tokenizer_2, unet=shared.sd_pipeline.unet, scheduler=shared.sd_pipeline.scheduler)
                    shared.sd_pipeline.pipeline_name = 'StableDiffusionXLImg2ImgPipeline'
                else:
                    #shared.sd_pipeline = StableDiffusionXLInpaintPipeline(**shared.sd_pipeline.components)
                    shared.sd_pipeline = StableDiffusionXLInpaintPipeline(vae=shared.sd_pipeline.vae, text_encoder_2=shared.sd_pipeline.text_encoder_2, text_encoder=shared.sd_pipeline.text_encoder, tokenizer=shared.sd_pipeline.tokenizer, tokenizer_2=shared.sd_pipeline.tokenizer_2, unet=shared.sd_pipeline.unet, scheduler=shared.sd_pipeline.scheduler)
                    shared.sd_pipeline.pipeline_name = 'StableDiffusionXLInpaintPipeline'
            else:
                if image_mask is None:
                    #shared.sd_pipeline = StableDiffusionImg2ImgPipeline(**shared.sd_pipeline.components)
                    shared.sd_pipeline = StableDiffusionImg2ImgPipeline(vae=shared.sd_pipeline.vae, text_encoder=shared.sd_pipeline.text_encoder, tokenizer=shared.sd_pipeline.tokenizer, unet=shared.sd_pipeline.unet, scheduler=shared.sd_pipeline.scheduler, safety_checker=shared.sd_pipeline.safety_checker, feature_extractor=shared.sd_pipeline.feature_extractor)
                    shared.sd_pipeline.pipeline_name = 'StableDiffusionImg2ImgPipeline'
                else:
                    #shared.sd_pipeline = StableDiffusionInpaintPipeline(**shared.sd_pipeline.components)
                    shared.sd_pipeline = StableDiffusionInpaintPipeline(vae=shared.sd_pipeline.vae, text_encoder=shared.sd_pipeline.text_encoder, tokenizer=shared.sd_pipeline.tokenizer, unet=shared.sd_pipeline.unet, scheduler=shared.sd_pipeline.scheduler, safety_checker=shared.sd_pipeline.safety_checker, feature_extractor=shared.sd_pipeline.feature_extractor)
                    shared.sd_pipeline.pipeline_name = 'StableDiffusionInpaintPipeline'

    return controlnet_images, ref_image, inpaint_image