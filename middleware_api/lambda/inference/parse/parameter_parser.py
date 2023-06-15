import os
from PIL import Image, ImageOps, ImageFilter, ImageEnhance, ImageChops
import numpy as np
import io
import base64
from gradio.processing_utils import encode_pil_to_base64

def get_param_value(params_dict, key, defaultValue="false"):
    try:
        param_value = params_dict[key]
    except Exception as e:
        print(f"can not found {key} and use default value {defaultValue}")
        param_value = defaultValue
         
    return param_value

def json_convert_to_payload(params_dict, checkpoint_info, task_type):
    # Need to generate the payload from data_dict here:
    script_name = get_param_value(params_dict, 'script_list', defaultValue="None")
    if script_name == "None":
        script_name = ""
    script_args = []
    param_name = 'txt2img'

    if task_type == 'txt2img':
        param_name = 'txt2img'
    elif task_type == 'img2img' or task_type == 'interrogate_clip' or task_type == 'interrogate_deepbooru':
        param_name = 'img2img'

    if script_name == 'Prompt matrix':
        put_at_start = get_param_value(params_dict, 'script_txt2txt_prompt_matrix_put_at_start')
        different_seeds = get_param_value(params_dict, 'script_txt2txt_prompt_matrix_different_seeds')
        if get_param_value(params_dict, 'script_txt2txt_prompt_matrix_prompt_type_positive', defaultValue="positive"):
            prompt_type = "positive"
        else:
            prompt_type = "negative"
        if get_param_value(params_dict, 'script_txt2txt_prompt_matrix_variations_delimiter_comma', defaultValue="comma"): 
            variations_delimiter = "comma"
        else:
            variations_delimiter = "space"
        margin_size = int(get_param_value(params_dict, 'script_txt2txt_prompt_matrix_margin_size', defaultValue=0))
        script_args = [put_at_start, different_seeds, prompt_type, variations_delimiter, margin_size]

    if script_name == 'Prompts from file or textbox':
        checkbox_iterate = get_param_value(params_dict, 'script_txt2txt_checkbox_iterate_every_line')
        checkbox_iterate_batch = get_param_value(params_dict, 'script_txt2txt_checkbox_iterate_all_lines')
        list_prompt_inputs = get_param_value(params_dict, 'script_txt2txt_prompts_from_file_or_textbox_prompt_txt', defaultValue="")
        lines = [x.strip() for x in list_prompt_inputs.split("\n")]
        script_args = [checkbox_iterate, checkbox_iterate_batch, "\n".join(lines)]

    if script_name == 'X/Y/Z plot':
        type_dict = {'Nothing': 0,
                       'Seed': 1,
                       'Var. seed': 2,
                       'Var. strength': 3,
                       'Steps': 4,
                       'Hires stteps': 5,
                       'CFG Scale': 6,
                       'Prompt S/R': 7,
                       'Prompt order': 8,
                       'Sampler': 9,
                       'Checkpoint name': 10,
                       'Negative Guidance minimum sigma': 11,
                       'Sigma Churn': 12,
                       'Sigma min': 13,
                       'Sigma max': 14,
                       'Sigma noise': 15,
                       'Eta': 16,
                       'Clip skip': 17,
                       'Denoising': 18,
                       'Hires upscaler': 19,
                       'VAE': 20,
                       'Styles': 21,
                       'UniPC Order': 22,
                       'Face restore': 23,
                       '[ControlNet] Enabled': 24,
                       '[ControlNet] Model': 25,
                       '[ControlNet] Weight': 26,
                       '[ControlNet] Guidance Start': 27,
                       '[ControlNet] Guidance End': 28,
                       '[ControlNet] Resize Mode': 29,
                       '[ControlNet] Preprocessor': 30,
                       '[ControlNet] Pre Resolution': 31,
                       '[ControlNet] Pre Threshold A': 32,
                       '[ControlNet] Pre Threshold B': 33}
        dropdown_index = [9, 10, 19, 20, 21, 24, 25, 29, 30]
        x_type = type_dict[get_param_value(params_dict, 'script_txt2txt_xyz_plot_x_type', defaultValue="Nothing")]
        x_values = get_param_value(params_dict, 'script_txt2txt_xyz_plot_x_values', defaultValue="")
        x_values_dropdown = get_param_value(params_dict, 'script_txt2txt_xyz_plot_x_values', defaultValue="")
        if x_type in dropdown_index:
            if x_type == 10:
                x_values_dropdown = get_param_value(params_dict, 'sagemaker_stable_diffusion_checkpoint', defaultValue="None")
            elif x_type == 25:
                x_values_dropdown = get_param_value(params_dict, 'sagemaker_controlnet_model', defaultValue="None")
            x_values_dropdown = x_values_dropdown.split(":")
        
        y_type = type_dict[get_param_value(params_dict, 'script_txt2txt_xyz_plot_y_type', defaultValue="Nothing")]
        y_values = get_param_value(params_dict, 'script_txt2txt_xyz_plot_y_values', defaultValue="")
        y_values_dropdown = get_param_value(params_dict, 'script_txt2txt_xyz_plot_y_values', defaultValue="")
        if y_type in dropdown_index:
            if y_type == 10:
                y_values_dropdown = get_param_value(params_dict, 'sagemaker_stable_diffusion_checkpoint', defaultValue="None")
            elif y_type == 25:
                y_values_dropdown = get_param_value(params_dict, 'sagemaker_controlnet_model', defaultValue="None")
            y_values_dropdown = y_values_dropdown.split(":")
        
        z_type = type_dict[get_param_value(params_dict, 'script_txt2txt_xyz_plot_z_type', defaultValue="Nothing")]
        z_values = get_param_value(params_dict, 'script_txt2txt_xyz_plot_z_values', defaultValue="")
        z_values_dropdown = get_param_value(params_dict, 'script_txt2txt_xyz_plot_z_values', defaultValue="")
        if z_type in dropdown_index:
            if z_type == 10:
                z_values_dropdown = get_param_value(params_dict, 'sagemaker_stable_diffusion_checkpoint', defaultValue="None")
            elif z_type == 25:
                z_values_dropdown = get_param_value(params_dict, 'sagemaker_controlnet_model', defaultValue="None")
            z_values_dropdown = z_values_dropdown.split(":")
        
        draw_legend = get_param_value(params_dict, 'script_txt2txt_xyz_plot_draw_legend')
        include_lone_images = get_param_value(params_dict, 'script_txt2txt_xyz_plot_include_lone_images')
        include_sub_grids = get_param_value(params_dict, 'script_txt2txt_xyz_plot_include_sub_grids')
        no_fixed_seeds = get_param_value(params_dict, 'script_txt2txt_xyz_plot_no_fixed_seeds')
        margin_size = int(get_param_value(params_dict, 'script_txt2txt_xyz_plot_margin_size', defaultValue=0))
        script_args = [x_type, x_values, x_values_dropdown, y_type, y_values, y_values_dropdown, z_type, z_values, z_values_dropdown, draw_legend, include_lone_images, include_sub_grids, no_fixed_seeds, margin_size]

    # get all parameters from ui-config.json
    prompt = get_param_value(params_dict, f'{param_name}_prompt', defaultValue="") 
    negative_prompt = get_param_value(params_dict, f'{param_name}_neg_prompt', defaultValue="") 
    denoising_strength = float(get_param_value(params_dict, f'{param_name}_denoising_strength', defaultValue=0.7))
    styles = get_param_value(params_dict, f'{param_name}_styles', defaultValue=["None", "None"])
    if styles == "":
        styles = []
    seed = float(get_param_value(params_dict, f'{param_name}_seed', defaultValue=-1.0)) 
    subseed = float(get_param_value(params_dict, f'{param_name}_subseed', defaultValue=-1.0))
    subseed_strength = float(get_param_value(params_dict, f'{param_name}_subseed_strength', defaultValue=0))
    seed_resize_from_h = int(get_param_value(params_dict, f'{param_name}_seed_resize_from_h', defaultValue=0))
    seed_resize_from_w = int(get_param_value(params_dict, f'{param_name}_seed_resize_from_w', defaultValue=0)) 
    sampler_index = get_param_value(params_dict, f'{param_name}_sampling_method', defaultValue="Euler a")
    batch_size = int(get_param_value(params_dict, f'{param_name}_batch_size', defaultValue=1)) 
    n_iter = int(get_param_value(params_dict, f'{param_name}_batch_count', defaultValue=1))
    steps = int(get_param_value(params_dict, f'{param_name}_steps', defaultValue=20))
    cfg_scale = float(get_param_value(params_dict, f'{param_name}_cfg_scale', defaultValue=7))
    width = int(get_param_value(params_dict, f'{param_name}_width', defaultValue=512))
    height = int(get_param_value(params_dict, f'{param_name}_height', defaultValue=512))
    restore_faces = get_param_value(params_dict, f'{param_name}_restore_faces')
    tiling = get_param_value(params_dict, f'{param_name}_tiling')
    override_settings = {}
    eta = 1
    s_churn = 0
    s_tmax = 1
    s_tmin = 0
    s_noise = 1 

    selected_sd_model = get_param_value(params_dict, 'sagemaker_stable_diffusion_checkpoint', defaultValue="") 
    selected_cn_model = get_param_value(params_dict, 'sagemaker_controlnet_model', defaultValue="")
    selected_hypernets = get_param_value(params_dict, 'sagemaker_hypernetwork_model', defaultValue="")
    selected_loras = get_param_value(params_dict, 'sagemaker_lora_model', defaultValue="")
    selected_embeddings = get_param_value(params_dict, 'sagemaker_texual_inversion_model', defaultValue="")
    
    if selected_sd_model == "":
        selected_sd_model = ['v1-5-pruned-emaonly.safetensors']
    else:
        selected_sd_model = selected_sd_model.split(":")
    if selected_cn_model == "":
        selected_cn_model = []
    else:
        selected_cn_model = selected_cn_model.split(":")
    if selected_hypernets == "":
        selected_hypernets = []
    else:
        selected_hypernets = selected_hypernets.split(":")
    if selected_loras == "":
        selected_loras = []
    else:
        selected_loras = selected_loras.split(":")
    if selected_embeddings == "":
        selected_embeddings = []
    else:
        selected_embeddings = selected_embeddings.split(":")
    
    for embedding in selected_embeddings:
        if embedding not in prompt:
            prompt = prompt + embedding
    for hypernet in selected_hypernets:
        hypernet_name = os.path.splitext(hypernet)[0]
        if hypernet_name not in prompt:
            prompt = prompt + f"<hypernet:{hypernet_name}:1>"
    for lora in selected_loras:
        lora_name = os.path.splitext(lora)[0]
        if lora_name not in prompt:
            prompt = prompt + f"<lora:{lora_name}:1>"
    
    contronet_enable = get_param_value(params_dict, 'controlnet_enable')
    if contronet_enable:
        controlnet_module = get_param_value(params_dict, 'controlnet_preprocessor', defaultValue=None)
        if len(selected_cn_model) < 1:
            controlnet_model = "None"
        else:
            controlnet_model = os.path.splitext(selected_cn_model[0])[0]
        controlnet_image = get_param_value(params_dict, f'{param_name}_controlnet_ControlNet_input_image', defaultValue=None)
        controlnet_image = controlnet_image.split(',')[1]
        weight = float(get_param_value(params_dict, 'controlnet_weight', defaultValue=1)) #1,
        if get_param_value(params_dict, 'controlnet_resize_mode_just_resize'):
            resize_mode = "Just Resize" # "Crop and Resize",
        if get_param_value(params_dict, 'controlnet_resize_mode_Crop_and_Resize'):
            resize_mode = "Crop and Resize"
        if get_param_value(params_dict, 'controlnet_resize_mode_Resize_and_Fill'):
            resize_mode = "Resize and Fill"
        lowvram = get_param_value(params_dict, 'controlnet_lowVRAM_enable') #: "False",
        processor_res = int(get_param_value(params_dict, 'controlnet_preprocessor_resolution', defaultValue=512))
        threshold_a = float(get_param_value(params_dict, 'controlnet_canny_low_threshold', defaultValue=0))
        threshold_b = float(get_param_value(params_dict, 'controlnet_canny_high_threshold', defaultValue=1))
        guidance_start = float(get_param_value(params_dict, 'controlnet_starting_control_step', defaultValue=0)) #: 0,
        guidance_end = float(get_param_value(params_dict, 'controlnet_ending_control_step', defaultValue=1)) #: 1,
        if get_param_value(params_dict, 'controlnet_control_mode_balanced'):
            guessmode = "Balanced"
        if get_param_value(params_dict, 'controlnet_control_mode_my_prompt_is_more_important'):
            guessmode = "My prompt is more important"
        if get_param_value(params_dict, 'controlnet_control_mode_controlnet_is_more_important'):
            guessmode = "Controlnet is more important"
        pixel_perfect = get_param_value(params_dict, 'controlnet_pixel_perfect')
        allow_preview = get_param_value(params_dict, 'controlnet_allow_preview')
        loopback = get_param_value(params_dict, 'controlnet_loopback_automatically')
    
    if param_name == 'txt2img':
        enable_hr = get_param_value(params_dict, f'{param_name}_enable_hr')
        hr_scale = float(get_param_value(params_dict, f'{param_name}_hr_scale', defaultValue=2.0))
        hr_upscaler = get_param_value(params_dict, f'{param_name}_hr_upscaler', defaultValue="Latent")
        hr_second_pass_steps = int(get_param_value(params_dict, f'{param_name}_hires_steps', defaultValue=0))
        firstphase_width = int(get_param_value(params_dict, f'{param_name}_hr_resize_x', defaultValue=0))
        firstphase_height = int(get_param_value(params_dict, f'{param_name}_hr_resize_y', defaultValue=0))
        hr_resize_x = int(get_param_value(params_dict, f'{param_name}_hr_resize_x', defaultValue=0))
        hr_resize_y = int(get_param_value(params_dict, f'{param_name}_hr_resize_y', defaultValue=0))
        

    if param_name == 'img2img':
        img2img_mode = get_param_value(params_dict, 'img2img_selected_tab_name', defaultValue='img2img')
        img2img_selected_resize_tab = get_param_value(params_dict, 'img2img_selected_resize_tab', defaultValue='ResizeTo')
        img2img_init_img_with_mask = get_param_value(params_dict, 'img2img_init_img_with_mask', defaultValue=None)
        img2img_inpaint_color_sketch = get_param_value(params_dict, 'img2img_inpaint_color_sketch', defaultValue=None)
        inpaint_color_sketch_orig = get_param_value(params_dict, 'img2img_inpaint_sketch_image', defaultValue=None)
        img2img_init_img_inpaint = get_param_value(params_dict, 'img2img_init_img_inpaint', defaultValue=None)
        img2img_init_mask_inpaint = get_param_value(params_dict, 'img2img_init_mask_inpaint', defaultValue=None)
        sketch = get_param_value(params_dict, 'img2img_sketch', defaultValue=None)
        img2img_init_img = get_param_value(params_dict, 'img2img_init_img', defaultValue=None)
        mask_blur = int(get_param_value(params_dict, 'img2img_mask_blur', defaultValue=4))
        mask_alpha = 0

        print("img2img mode is", img2img_mode)
        
        image = None
        mask = None
        if img2img_mode == 'img2img':  # img2img
            image = Image.open(io.BytesIO(base64.b64decode(img2img_init_img.split(',')[1])))
            image = encode_pil_to_base64(image.convert("RGB"))
            mask = None
        elif img2img_mode == 'Sketch':  # img2img sketch
            sketch = Image.open(io.BytesIO(base64.b64decode(sketch.split(',')[1])))
            image = encode_pil_to_base64(sketch.convert("RGB"))
            mask = None
        elif img2img_mode == 'Inpaint_upload':  # inpaint upload mask
            image = img2img_init_img_inpaint
            mask = img2img_init_mask_inpaint
        elif img2img_mode == 'Inpaint':  # inpaint
            image = Image.open(io.BytesIO(base64.b64decode(img2img_init_img_with_mask["image"].split(',')[1])))
            mask = Image.open(io.BytesIO(base64.b64decode(img2img_init_img_with_mask["mask"].split(',')[1])))
            alpha_mask = ImageOps.invert(image.split()[-1]).convert('L').point(lambda x: 255 if x > 0 else 0, mode='1')
            mask = ImageChops.lighter(alpha_mask, mask.convert('L')).convert('L')
            image = image.convert("RGB")
            image = encode_pil_to_base64(image)
            mask = encode_pil_to_base64(mask)
        elif img2img_mode == 'Inpaint_sketch':  # inpaint sketch
            image_pil = Image.open(io.BytesIO(base64.b64decode(img2img_inpaint_color_sketch.split(',')[1])))
            # image_pil = image_pil.convert("RGB")
            orig = Image.open(io.BytesIO(base64.b64decode(inpaint_color_sketch_orig.split(',')[1])))
            # orig = orig.resize(image_pil.size)
            orig = orig or image_pil
            pred = np.any(np.array(image_pil) != np.array(orig), axis=-1)
            mask = Image.fromarray(pred.astype(np.uint8) * 255, "L")
            mask = ImageEnhance.Brightness(mask).enhance(1 - mask_alpha / 100)
            blur = ImageFilter.GaussianBlur(mask_blur)
            image_pil = Image.composite(image_pil.filter(blur), orig, mask.filter(blur))
            mask = encode_pil_to_base64(mask)
            image = encode_pil_to_base64(image_pil)

        inpainting_fill = get_param_value(params_dict, 'img2img_inpainting_fill_fill')
        image_cfg_scale = 1.5
        if img2img_selected_resize_tab == 'ResizeBy':
            img2img_scale = float(get_param_value(params_dict, 'img2img_scale', defaultValue=1.0))
            assert image, "Can't scale by because no image is selected"
            image_pil = Image.open(io.BytesIO(base64.b64decode(image)))
            width = int(image_pil.width * img2img_scale)
            height = int(image_pil.height * img2img_scale)


        img2img_resize_mode = 0
        if get_param_value(params_dict, 'img2img_resize_mode_crop_and_resize'):
            img2img_resize_mode = 1
        if get_param_value(params_dict, 'img2img_resize_mode_resize_and_fill'):
            img2img_resize_mode = 2
        if get_param_value(params_dict, 'img2img_resize_mode_just_resize_latent_upscale'):
            img2img_resize_mode = 3
        inpainting_mask_invert = 0
        if get_param_value(params_dict, 'img2img_mask_mode_inpaint_not_masked'):
            inpainting_mask_invert = 1
        inpainting_full_res = 0
        if get_param_value(params_dict, 'img2img_inpaint_full_res_only_masked'):
            inpainting_full_res = 1
        inpaint_full_res_padding = 32
        inpainting_fill = 0
        if get_param_value(params_dict, 'img2img_inpainting_fill_original'):
            inpainting_fill = 1
        if get_param_value(params_dict, 'img2img_inpainting_fill_latent_noise'):
            inpainting_fill = 2
        if get_param_value(params_dict, 'img2img_inpainting_fill_latent_nothing'):
            inpainting_fill = 3
        include_init_images = False


    endpoint_name = checkpoint_info['sagemaker_endpoint'] #"infer-endpoint-ca0e"

    # construct payload
    payload = {}
    # common parameters
    payload["endpoint_name"] = endpoint_name
    payload["task"] = task_type
    payload["username"] = "test"
    payload["checkpoint_info"] = checkpoint_info
    payload["models"] = {
        "space_free_size": 4e10,
        "Stable-diffusion": selected_sd_model,
        "ControlNet": selected_cn_model,
        "hypernetworks": selected_hypernets,
        "Lora": selected_loras,
        "embeddings": selected_embeddings}

    if task_type == 'interrogate_clip':
        payload["interrogate_payload"] = {}
        payload["interrogate_payload"]["image"] = img2img_init_img
        payload["interrogate_payload"]["model"] = 'clip'
    elif task_type == 'interrogate_deepbooru':
        payload["interrogate_payload"] = {}
        payload["interrogate_payload"]["image"] = img2img_init_img
        payload["interrogate_payload"]["model"] = 'deepdanbooru'
    else:
        # upload origin params for txt2img/img2img
        payload_name = f"{param_name}_payload"
        payload[payload_name] = {}
        payload[payload_name]["denoising_strength"]=denoising_strength
        payload[payload_name]["prompt"]=prompt
        payload[payload_name]["styles"]=styles
        payload[payload_name]["seed"]=seed
        payload[payload_name]["subseed"]=subseed
        payload[payload_name]["subseed_strength"]=subseed_strength
        payload[payload_name]["seed_resize_from_h"]=seed_resize_from_h
        payload[payload_name]["seed_resize_from_w"]=seed_resize_from_w
        payload[payload_name]["sampler_index"]=sampler_index
        payload[payload_name]["batch_size"]=batch_size
        payload[payload_name]["n_iter"]=n_iter
        payload[payload_name]["steps"]=steps
        payload[payload_name]["cfg_scale"]=cfg_scale
        payload[payload_name]["width"]=width
        payload[payload_name]["height"]=height
        payload[payload_name]["restore_faces"]=restore_faces
        payload[payload_name]["tiling"]=tiling
        payload[payload_name]["negative_prompt"]=negative_prompt
        payload[payload_name]["eta"]=eta
        payload[payload_name]["s_churn"]=s_churn
        payload[payload_name]["s_tmax"]=s_tmax
        payload[payload_name]["s_tmin"]=s_tmin
        payload[payload_name]["s_noise"]=s_noise
        payload[payload_name]["override_settings"]=override_settings
        payload[payload_name]["script_name"]=script_name
        payload[payload_name]["script_args"]=script_args

        if task_type == 'txt2img':
            payload[payload_name]["enable_hr"]= enable_hr
            payload[payload_name]["firstphase_width"]=firstphase_width
            payload[payload_name]["firstphase_height"]=firstphase_height
            payload[payload_name]["hr_scale"]=hr_scale
            payload[payload_name]["hr_upscaler"]=hr_upscaler
            payload[payload_name]["hr_second_pass_steps"]=hr_second_pass_steps
            payload[payload_name]["hr_resize_x"]=hr_resize_x
            payload[payload_name]["hr_resize_y"]=hr_resize_y

        if task_type == 'img2img':
            payload[payload_name]["init_images"] = [image]
            payload[payload_name]["mask"] = mask
            payload[payload_name]["inpainting_fill"] = inpainting_fill
            payload[payload_name]["image_cfg_scale"] = image_cfg_scale
            payload[payload_name]["resize_mode"] = img2img_resize_mode
            payload[payload_name]["inpaint_full_res"] = inpainting_full_res
            payload[payload_name]["inpaint_full_res_padding"] = inpaint_full_res_padding 
            payload[payload_name]["inpainting_mask_invert"] = inpainting_mask_invert
            payload[payload_name]["include_init_images"] = include_init_images
            
            
        if contronet_enable:
            print(f'{task_type} with controlnet!!!!!!!!!!')
            payload["alwayson_scripts"] = {}
            payload["alwayson_scripts"]["controlnet"]["args"] = [
                {
                    "input_image": controlnet_image,
                    "mask": "",
                    "module": controlnet_module,
                    "model": controlnet_model,
                    "loopback": loopback,
                    "weight": weight,
                    "resize_mode": resize_mode,
                    "lowvram": lowvram,
                    "processor_res": processor_res,
                    "threshold_a": threshold_a,
                    "threshold_b": threshold_b,
                    "guidance_start": guidance_start,
                    "guidance_end": guidance_end,
                    "guessmode": guessmode,
                    "pixel_perfect": pixel_perfect
                }]
    return payload