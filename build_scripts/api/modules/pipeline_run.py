import torch
import modules.shared as shared
from diffusers import StableDiffusionXLImg2ImgPipeline
import os

# some of those options should not be changed at all because they would break the model, so I removed them from options.
opt_C = 4
opt_f = 8

def tx2img_pipeline_run(pipeline_name, strength, denoising_start,aesthetic_score,negative_aesthetic_score,controlnet_conditioning_scale, 
                         control_guidance_start, control_guidance_end, guess_mode, prompt, prompt_2, height, width, num_inference_steps,denoising_end,guidance_scale,
                         negative_prompt,negative_prompt_2,num_images_per_prompt,eta,generator,latents,prompt_embeds,negative_prompt_embeds,pooled_prompt_embeds,
                         negative_pooled_prompt_embeds,output_type,callback,callback_steps,cross_attention_kwargs,guidance_rescale,original_size,
                         crops_coords_top_left,target_size, controlnet_image, ref_img, inpaint_img, use_refiner, refiner_checkpoint):
    sd_pipeline = shared.sd_pipeline
    # default output: latents
    if pipeline_name == 'StableDiffusionPipeline_webui':
        sd_pipeline.set_scheduler("sample_euler_ancestral")
        images = sd_pipeline(
            prompt = prompt,
            height = height,
            width = width,
            num_inference_steps = num_inference_steps,
            guidance_scale = guidance_scale,
            negative_prompt = negative_prompt,
            num_images_per_prompt= num_images_per_prompt,
            eta = eta,
            generator = generator,
            latents = latents,
            output_type = output_type,
            return_dict = True,
            callback = callback,
            callback_steps = callback_steps,
            cross_attention_kwargs = cross_attention_kwargs).images
    elif pipeline_name == 'StableDiffusionPipeline':
        images = sd_pipeline(
            prompt = prompt,
            height = height,
            width = width,
            num_inference_steps = num_inference_steps,
            guidance_scale = guidance_scale,
            negative_prompt = negative_prompt,
            num_images_per_prompt= num_images_per_prompt,
            eta = eta,
            generator = generator,
            latents = latents,
            prompt_embeds = prompt_embeds,
            negative_prompt_embeds= negative_prompt_embeds,
            output_type = output_type,
            return_dict = True,
            callback = callback,
            callback_steps = callback_steps,
            cross_attention_kwargs = cross_attention_kwargs).images
    elif pipeline_name == 'StableDiffusionXLPipeline':
        images = sd_pipeline(
            prompt = prompt,
            prompt_2 = prompt_2,
            height = height,
            width = width,
            num_inference_steps = num_inference_steps,
            denoising_end = denoising_end,
            guidance_scale = guidance_scale,
            negative_prompt = negative_prompt,
            negative_prompt_2 = negative_prompt_2,
            num_images_per_prompt = num_images_per_prompt,
            eta = eta,
            generator = generator,
            latents = latents,
            prompt_embeds = prompt_embeds,
            negative_prompt_embeds = negative_prompt_embeds,
            pooled_prompt_embeds = pooled_prompt_embeds,
            negative_pooled_prompt_embeds = negative_pooled_prompt_embeds,
            output_type = output_type,
            return_dict = True,
            callback = callback,
            callback_steps = callback_steps,
            cross_attention_kwargs = cross_attention_kwargs,
            guidance_rescale = guidance_rescale,
            original_size = original_size,
            crops_coords_top_left = crops_coords_top_left,
            target_size = target_size).images
    elif pipeline_name == 'StableDiffusionControlNetPipeline':
        images = sd_pipeline(
            prompt = prompt,
            image = controlnet_image,
            height = height,
            width = width,
            num_inference_steps = num_inference_steps,
            guidance_scale = guidance_scale,
            negative_prompt = negative_prompt,
            num_images_per_prompt = num_images_per_prompt,
            eta = eta,
            generator = generator,
            latents = latents,
            prompt_embeds = prompt_embeds,
            negative_prompt_embeds = negative_prompt_embeds,
            #negative_pooled_prompt_embeds = negative_pooled_prompt_embeds,
            output_type = output_type,
            return_dict = True,
            callback = callback,
            callback_steps = callback_steps,
            cross_attention_kwargs = cross_attention_kwargs,
            controlnet_conditioning_scale = controlnet_conditioning_scale,
            guess_mode = guess_mode,
            control_guidance_start = control_guidance_start,
            control_guidance_end = control_guidance_end).images
    elif pipeline_name == 'StableDiffusionXLControlNetPipeline':
        images = sd_pipeline(
            prompt = prompt,
            prompt_2 = prompt_2,
            image = controlnet_image,
            height = height,
            width = width,
            num_inference_steps = num_inference_steps,
            guidance_scale = guidance_scale,
            negative_prompt = negative_prompt,
            negative_prompt_2 = negative_prompt_2,
            num_images_per_prompt = num_images_per_prompt,
            eta = eta,
            generator = generator,
            latents = latents,
            prompt_embeds = prompt_embeds,
            negative_prompt_embeds = negative_prompt_embeds,
            #pooled_prompt_embeds = pooled_prompt_embeds,
            #negative_pooled_prompt_embeds = negative_pooled_prompt_embeds,
            output_type = output_type,
            return_dict = True,
            callback = callback,
            callback_steps = callback_steps,
            cross_attention_kwargs = cross_attention_kwargs,
            controlnet_conditioning_scale = controlnet_conditioning_scale,
            guess_mode = guess_mode,
            control_guidance_start = control_guidance_start,
            control_guidance_end = control_guidance_end,
            original_size = original_size).images
    elif pipeline_name == 'StableDiffusionControlNetReferencePipeline':
        images = sd_pipeline(
            prompt = prompt,
            image = controlnet_image,
            ref_image = ref_img,
            height = height,
            width = width,
            num_inference_steps = num_inference_steps,
            guidance_scale = guidance_scale,
            negative_prompt = negative_prompt,
            num_images_per_prompt = num_images_per_prompt,
            eta = eta,
            generator = generator,
            latents = latents,
            prompt_embeds = prompt_embeds,
            negative_prompt_embeds = negative_prompt_embeds,
            output_type = output_type,
            return_dict = True,
            callback = callback,
            callback_steps = callback_steps,
            cross_attention_kwargs = cross_attention_kwargs,
            controlnet_conditioning_scale = controlnet_conditioning_scale,
            guess_mode = guess_mode,
            attention_auto_machine_weight = 1.0,
            gn_auto_machine_weight = 1.0,
            style_fidelity = 0.5,
            reference_attn = True,
            reference_adain = True).images
    elif pipeline_name == 'StableDiffusionReferencePipeline':
        images = sd_pipeline(
            prompt = prompt,
            ref_image = ref_img,
            height = height,
            width = width,
            num_inference_steps = num_inference_steps,
            guidance_scale = guidance_scale,
            negative_prompt = negative_prompt,
            num_images_per_prompt = num_images_per_prompt,
            eta = eta,
            generator = generator,
            latents = latents,
            prompt_embeds = prompt_embeds,
            negative_prompt_embeds = negative_prompt_embeds,
            output_type = output_type,
            return_dict = True,
            callback = callback,
            callback_steps = callback_steps,
            cross_attention_kwargs = cross_attention_kwargs,
            guidance_rescale = 0.0,
            attention_auto_machine_weight = 1.0,
            gn_auto_machine_weight = 1.0,
            style_fidelity = 0.5,
            reference_attn = True, 
            reference_adain = True).images
    elif pipeline_name == 'StableDiffusionXLReferencePipeline':
        images = sd_pipeline(
            prompt = prompt,
            prompt_2 = prompt_2,
            ref_image = ref_img,
            height = height,
            width = width,
            num_inference_steps = num_inference_steps,
            denoising_end = denoising_end,
            guidance_scale = guidance_scale,
            negative_prompt = negative_prompt,
            negative_prompt_2 = negative_prompt_2,
            num_images_per_prompt = num_images_per_prompt,
            eta = eta,
            generator = generator,
            latents = latents,
            prompt_embeds = prompt_embeds,
            negative_prompt_embeds = negative_prompt_embeds,
            pooled_prompt_embeds = pooled_prompt_embeds,
            negative_pooled_prompt_embeds = negative_pooled_prompt_embeds,
            output_type = output_type,
            return_dict = True,
            callback = callback,
            callback_steps = callback_steps,
            cross_attention_kwargs = cross_attention_kwargs,
            guidance_rescale = guidance_rescale,
            original_size = original_size,
            crops_coords_top_left = crops_coords_top_left,
            target_size = target_size,
            attention_auto_machine_weight = 1.0,
            gn_auto_machine_weight = 1.0,
            style_fidelity = 0.5,
            reference_attn = True,
            reference_adain = False).images
    elif pipeline_name == 'StableDiffusionInpaintPipeline':
            images = sd_pipeline(
            prompt = prompt,
            image = inpaint_img[:,:,:3],
            mask_image = inpaint_img[:,:,3],
            height = height,
            width = width,
            strength = strength,
            num_inference_steps = num_inference_steps,
            guidance_scale = guidance_scale,
            negative_prompt = negative_prompt,
            num_images_per_prompt= num_images_per_prompt,
            eta = eta,
            generator = generator,
            latents = None,
            prompt_embeds = prompt_embeds,
            negative_prompt_embeds= negative_prompt_embeds,
            output_type = output_type,
            return_dict = True,
            callback = callback,
            callback_steps = callback_steps,
            cross_attention_kwargs = cross_attention_kwargs).images

    if use_refiner:
        refiner_checkpoint_path = os.path.join(os.path.dirname(shared.opts.data["sd_model_checkpoint_path"]), refiner_checkpoint)
        refiner_pipeline = StableDiffusionXLImg2ImgPipeline.from_single_file(refiner_checkpoint_path, torch_dtype=torch.float16, variant="fp16")
        refiner_pipeline.to("cuda")
        refiner_pipeline.enable_xformers_memory_efficient_attention()
        images = refiner_pipeline(
            prompt = prompt,
            prompt_2 = prompt_2,
            image = images,
            strength = strength,
            num_inference_steps = num_inference_steps,
            denoising_start = denoising_start,
            guidance_scale = guidance_scale,
            negative_prompt = negative_prompt,
            negative_prompt_2 = negative_prompt_2,
            num_images_per_prompt = num_images_per_prompt,
            eta = eta,
            generator = generator,
            prompt_embeds = prompt_embeds,
            negative_prompt_embeds = negative_prompt_embeds,
            pooled_prompt_embeds = pooled_prompt_embeds,
            negative_pooled_prompt_embeds = negative_pooled_prompt_embeds,
            output_type = output_type,
            return_dict = True,
            callback = callback,
            callback_steps = callback_steps,
            cross_attention_kwargs = cross_attention_kwargs,
            guidance_rescale = guidance_rescale,
            original_size = original_size,
            crops_coords_top_left = crops_coords_top_left,
            target_size = target_size,
            aesthetic_score = aesthetic_score,
            negative_aesthetic_score = negative_aesthetic_score).images

    return images
    

def img2img_pipeline_run(pipeline_name, init_images, init_latents, image_mask, strength, denoising_start,aesthetic_score,negative_aesthetic_score,controlnet_conditioning_scale, 
                         control_guidance_start, control_guidance_end, guess_mode, prompt, prompt_2, height, width, num_inference_steps,denoising_end,guidance_scale,
                         negative_prompt,negative_prompt_2,num_images_per_prompt,eta,generator,prompt_embeds,negative_prompt_embeds,pooled_prompt_embeds,
                         negative_pooled_prompt_embeds,output_type,callback,callback_steps,cross_attention_kwargs,guidance_rescale,original_size,crops_coords_top_left,
                         target_size, controlnet_image, use_refiner, refiner_checkpoint):
       
    # update sampler
    sd_pipeline = shared.sd_pipeline

    # default output: latents
    if pipeline_name == 'StableDiffusionImg2ImgPipeline':
        images = sd_pipeline(
            prompt = prompt,
            image = init_images,
            strength = strength,
            num_inference_steps = num_inference_steps,
            guidance_scale = guidance_scale,
            negative_prompt = negative_prompt,
            num_images_per_prompt= num_images_per_prompt,
            eta = eta,
            generator = generator,
            prompt_embeds = prompt_embeds,
            negative_prompt_embeds= negative_prompt_embeds,
            output_type = output_type,
            return_dict = True,
            callback = callback,
            callback_steps = callback_steps,
            cross_attention_kwargs = cross_attention_kwargs).images
    elif pipeline_name == 'StableDiffusionInpaintPipeline':
            images = sd_pipeline(
            prompt = prompt,
            image = init_images,
            mask_image = image_mask,
            height = height,
            width = width,
            strength = strength,
            num_inference_steps = num_inference_steps,
            guidance_scale = guidance_scale,
            negative_prompt = negative_prompt,
            num_images_per_prompt= num_images_per_prompt,
            eta = eta,
            generator = generator,
            latents = None,
            prompt_embeds = prompt_embeds,
            negative_prompt_embeds= negative_prompt_embeds,
            output_type = output_type,
            return_dict = True,
            callback = callback,
            callback_steps = callback_steps,
            cross_attention_kwargs = cross_attention_kwargs).images
    elif pipeline_name == 'StableDiffusionXLImg2ImgPipeline':
        ### image = self.init_latent + noise -> need set denoising_start is not none
        images = sd_pipeline(
            prompt = prompt,
            prompt_2 = prompt_2,
            image = init_images,
            strength = strength,
            num_inference_steps = num_inference_steps,
            denoising_start = denoising_start,
            denoising_end = denoising_end,
            guidance_scale = guidance_scale,
            negative_prompt = negative_prompt,
            negative_prompt_2 = negative_prompt_2,
            num_images_per_prompt = num_images_per_prompt,
            eta = eta,
            generator = generator,
            latents = None,
            prompt_embeds = prompt_embeds,
            negative_prompt_embeds = negative_prompt_embeds,
            pooled_prompt_embeds = pooled_prompt_embeds,
            negative_pooled_prompt_embeds = negative_pooled_prompt_embeds,
            output_type = output_type,
            return_dict = True,
            callback = callback,
            callback_steps = callback_steps,
            cross_attention_kwargs = cross_attention_kwargs,
            guidance_rescale = guidance_rescale,
            original_size = original_size,
            crops_coords_top_left = crops_coords_top_left,
            target_size = target_size,
            aesthetic_score = aesthetic_score,
            negative_aesthetic_score = negative_aesthetic_score).images
    elif pipeline_name == 'StableDiffusionXLInpaintPipeline':
            images = sd_pipeline(
            prompt = prompt,
            prompt_2 = prompt_2,
            image = init_images,
            mask_image = image_mask,
            height = height,
            width = width,
            strength = strength,
            num_inference_steps = num_inference_steps,
            denoising_start = denoising_start,
            denoising_end = denoising_end,
            guidance_scale = guidance_scale,
            negative_prompt = negative_prompt,
            negative_prompt_2 = negative_prompt_2,
            num_images_per_prompt = num_images_per_prompt,
            eta = eta,
            generator = generator,
            latents = None,
            prompt_embeds = prompt_embeds,
            negative_prompt_embeds = negative_prompt_embeds,
            pooled_prompt_embeds = pooled_prompt_embeds,
            negative_pooled_prompt_embeds = negative_pooled_prompt_embeds,
            output_type = output_type,
            return_dict = True,
            callback = callback,
            callback_steps = callback_steps,
            cross_attention_kwargs = cross_attention_kwargs,
            guidance_rescale = guidance_rescale,
            original_size = original_size,
            crops_coords_top_left = crops_coords_top_left,
            target_size = target_size,
            aesthetic_score = aesthetic_score,
            negative_aesthetic_score = negative_aesthetic_score).images
    elif pipeline_name == 'StableDiffusionControlNetImg2ImgPipeline':
        images = sd_pipeline(
            prompt = prompt,
            image = init_images,
            control_image = controlnet_image,
            height = height,
            width = width,
            strength = strength,
            num_inference_steps = num_inference_steps,
            guidance_scale = guidance_scale,
            negative_prompt = negative_prompt,
            num_images_per_prompt= num_images_per_prompt,
            eta = eta,
            generator = generator,
            latents = None,
            prompt_embeds = prompt_embeds,
            negative_prompt_embeds= negative_prompt_embeds,
            output_type = output_type,
            return_dict = True,
            callback = callback,
            callback_steps = callback_steps,
            cross_attention_kwargs = cross_attention_kwargs,
            controlnet_conditioning_scale = controlnet_conditioning_scale,
            guess_mode = guess_mode,
            control_guidance_start = control_guidance_start,
            control_guidance_end = control_guidance_end).images
    elif pipeline_name == 'StableDiffusionControlNetInpaintPipeline':
        images = sd_pipeline(
            prompt = prompt,
            image = init_images,
            mask_image = image_mask,
            control_image = controlnet_image,
            height = height,
            width = width,
            strength = strength,
            num_inference_steps = num_inference_steps,
            guidance_scale = guidance_scale,
            negative_prompt = negative_prompt,
            num_images_per_prompt= num_images_per_prompt,
            eta = eta,
            generator = generator,
            latents = None,
            prompt_embeds = prompt_embeds,
            negative_prompt_embeds= negative_prompt_embeds,
            output_type = output_type,
            return_dict = True,
            callback = callback,
            callback_steps = callback_steps,
            cross_attention_kwargs = cross_attention_kwargs,
            controlnet_conditioning_scale = controlnet_conditioning_scale,
            guess_mode = guess_mode,
            control_guidance_start = control_guidance_start,
            control_guidance_end = control_guidance_end).images
    elif pipeline_name == 'StableDiffusionXLControlNetImg2ImgPipeline':
        images = sd_pipeline(
            prompt = prompt,
            prompt_2 = prompt_2,
            image = init_latents,
            control_image = controlnet_image,
            height = height,
            width = width,
            num_inference_steps = num_inference_steps,
            guidance_scale = guidance_scale,
            negative_prompt = negative_prompt,
            negative_prompt_2 = negative_prompt_2,
            num_images_per_prompt = num_images_per_prompt,
            eta = eta,
            generator = generator,
            latents = None,
            prompt_embeds = prompt_embeds,
            negative_prompt_embeds = negative_prompt_embeds,
            pooled_prompt_embeds = pooled_prompt_embeds,
            negative_pooled_prompt_embeds = negative_pooled_prompt_embeds,
            output_type = output_type,
            return_dict = True,
            callback = callback,
            callback_steps = callback_steps,
            cross_attention_kwargs = cross_attention_kwargs,
            controlnet_conditioning_scale = controlnet_conditioning_scale,
            guess_mode = guess_mode,
            control_guidance_start = control_guidance_start,
            control_guidance_end = control_guidance_end,
            original_size = original_size,
            crops_coords_top_left = (0, 0),
            target_size = None,
            negative_original_size = None,
            negative_crops_coords_top_left = (0, 0),
            negative_target_size = None,
            aesthetic_score = 6.0,
            negative_aesthetic_score = 2.5).images
    elif pipeline_name == 'StableDiffusionXLControlNetInpaintPipeline':
        images = sd_pipeline(
            prompt = prompt,
            prompt_2 = prompt_2,
            image = init_images,
            mask_image = image_mask,
            control_image = controlnet_image,
            height = height,
            width = width,
            strength = strength,
            num_inference_steps = num_inference_steps,
            denoising_start = denoising_start,
            denoising_end = denoising_end,
            guidance_scale = guidance_scale,
            negative_prompt = negative_prompt,
            negative_prompt_2 = negative_prompt_2,
            num_images_per_prompt = num_images_per_prompt,
            eta = eta,
            generator = generator,
            latents = None,
            prompt_embeds = prompt_embeds,
            negative_prompt_embeds = negative_prompt_embeds,
            pooled_prompt_embeds = pooled_prompt_embeds,
            negative_pooled_prompt_embeds = negative_pooled_prompt_embeds,
            output_type = output_type,
            return_dict = True,
            callback = callback,
            callback_steps = callback_steps,
            cross_attention_kwargs = cross_attention_kwargs,
            controlnet_conditioning_scale = controlnet_conditioning_scale,
            guess_mode = guess_mode,
            control_guidance_start = control_guidance_start,
            control_guidance_end = control_guidance_end,
            original_size = original_size,
            crops_coords_top_left = (0, 0),
            target_size = None,
            negative_original_size = None,
            negative_crops_coords_top_left = (0, 0),
            negative_target_size = None,
            aesthetic_score = 6.0,
            negative_aesthetic_score = 2.5).images

    if use_refiner:
        refiner_checkpoint_path = os.path.join(os.path.dirname(shared.opts.data["sd_model_checkpoint_path"]), refiner_checkpoint)
        refiner_pipeline = StableDiffusionXLImg2ImgPipeline.from_single_file(refiner_checkpoint_path, torch_dtype=torch.float16, variant="fp16")
        refiner_pipeline.to('cuda')
        refiner_pipeline.enable_xformers_memory_efficient_attention()
        images = refiner_pipeline(
            prompt = prompt,
            prompt_2 = prompt_2,
            image = images,
            strength = strength,
            num_inference_steps = num_inference_steps,
            denoising_start = denoising_start,
            guidance_scale = guidance_scale,
            negative_prompt = negative_prompt,
            negative_prompt_2 = negative_prompt_2,
            num_images_per_prompt = num_images_per_prompt,
            eta = eta,
            generator = generator,
            prompt_embeds = prompt_embeds,
            negative_prompt_embeds = negative_prompt_embeds,
            pooled_prompt_embeds = pooled_prompt_embeds,
            negative_pooled_prompt_embeds = negative_pooled_prompt_embeds,
            output_type = output_type,
            return_dict = True,
            callback = callback,
            callback_steps = callback_steps,
            cross_attention_kwargs = cross_attention_kwargs,
            guidance_rescale = guidance_rescale,
            original_size = original_size,
            crops_coords_top_left = crops_coords_top_left,
            target_size = target_size,
            aesthetic_score = aesthetic_score,
            negative_aesthetic_score = negative_aesthetic_score).images

    return images