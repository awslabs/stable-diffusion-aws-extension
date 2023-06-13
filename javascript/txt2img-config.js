//This function is created to mitigate refresh get old value issue
window.onload = function() {
    let counter = 0;
    let limit = 10;
    let selectors = [
        "#refresh_api_gateway_url",
        "#refresh_api_token",
        "#refresh_sagemaker_endpoints",
        "#refresh_sd_checkpoints",
        "#refresh_txt2img_inference_job_ids",
        "#refresh_textual_inversion",
        "#refresh_sagemaker_endpoints_delete"
    ];

    let intervalId = setInterval(function() {
        console.log("click refresh when page reloaded"); 

        let allElementsFound = true;
        for (let selector of selectors) {
            let element = document.querySelector(selector);
            if (element != null) {
                element.click();
            } else {
                allElementsFound = false;
                console.warn(`Could not find element with selector: ${selector}`);
            }
        }

        counter++;
        if (counter === limit || allElementsFound) {
            console.log("refresh time:" + counter); 
            clearInterval(intervalId);
        }
    }, 2000);
};



// Save configuration in txt2img panel
function getDomValue(selector, defaultValue, isTextContent = false) {
    try {
        const element = document.querySelector(selector);
        if (isTextContent) {
            return element.textContent || defaultValue;
        } else {
            return element.value || defaultValue;
        }
    } catch (error) {
        return defaultValue;
    }
}

// Function to get the selected tab inside the img2img
function getSelectedButton() {
    // Get the parent element
    let parentDiv = document.querySelector("#mode_img2img > div.tab-nav.scroll-hide.svelte-1g805jl");

    // Get all the button children
    let buttons = parentDiv.querySelectorAll("button");

    // Initialize a variable to store the selected button
    let selectedButtonIndex = -1;

    // Loop through each button
    for (let i = 0; i < buttons.length; i++) {
        // Check if the button has the 'selected' class
        if (buttons[i].classList.contains("selected")) {
            // Store the index of the selected button (add 1 because nth-child is 1-indexed)
            selectedButtonIndex = i + 1;
            break;
        }
    }

    // Create a mapping from child index to a certain value
    let mapping = {
        1: "img2img",
        2: "Sketch",
        3: "Inpaint",
        4: "Inpaint_sketch",
        5: "Inpaint_upload",
        6: "Batch"
    };

    // Check if a button was selected
    if (selectedButtonIndex != -1) {
        // If yes, return the corresponding value from the mapping
        return mapping[selectedButtonIndex];
    } else {
        // If no button was selected, return a suitable message
        return "No button is selected.";
    }
}

// function to get tab "Restore to" or "Resize by"
function getSelectedTabResize() {
    // Get the parent element
    let parentDiv = document.querySelector("#component-459 > div.tab-nav.scroll-hide.svelte-1g805jl");

    // Get all the button children
    let buttons = parentDiv.querySelectorAll("button");

    // Initialize a variable to store the selected button
    let selectedButtonIndex = -1;

    // Loop through each button
    for (let i = 0; i < buttons.length; i++) {
        // Check if the button has the 'selected' class
        if (buttons[i].classList.contains("selected")) {
            // Store the index of the selected button (add 1 because nth-child is 1-indexed)
            selectedButtonIndex = i + 1;
            break;
        }
    }

    // Create a mapping from child index to a certain value
    let mapping = {
        1: "ResizeTo",
        2: "ResizeBy"
    };

    // Check if a button was selected
    if (selectedButtonIndex != -1) {
        // If yes, return the corresponding value from the mapping
        return mapping[selectedButtonIndex];
    } else {
        // If no button was selected, return a suitable message
        return "No tab is selected.";
    }
}

function set_textbox_value(textboxId, newValue) {
    let textbox = document.querySelector(textboxId);
    console.log("Trying to set the value of textBox")
    if (textbox) {
        textbox.textContent = newValue;
    } else {
        console.log("Textbox with id " + textboxId + " not found.");
    }
}

function set_textbox_value_gradio(elementId, newValue) {
    let textbox = gradioApp().getElementById(elementId).querySelector('p');
    console.log("Trying to set the value of textBox")
    if (textbox) {
        textbox.textContent = newValue;
    } else {
        console.log("Textbox with id " + elementId + " not found.");
    }
}


async function txt2img_config_save(endpoint_value) {
    var config = {};

    console.log(JSON.stringify(endpoint_value))

    // set_textbox_value('#html_info_txt2img', "Start uploading configuration to S3, please wait ......")
    set_textbox_value_gradio('html_info_txt2img', "Start uploading configuration to S3, please wait ......")

    scrap_ui_component_value_with_default(config);

    //following code is to get s3 presigned url from middleware and upload the ui parameters
    const key = "config/aigc.json";
    let remote_url = config["aws_api_gateway_url"];
    if (!remote_url.endsWith("/")) {
        remote_url += "/";
    }
    let get_presigned_s3_url = remote_url;
    get_presigned_s3_url += "inference/generate-s3-presigned-url-for-uploading";
    const api_key = config["aws_api_token"];

    try {
        const config_presigned_url = await getPresignedUrl(
            get_presigned_s3_url,
            api_key,
            key
        );
        const url = config_presigned_url.replace(/"/g, "");
        const config_data = JSON.stringify(config);
        await put_with_xmlhttprequest(url, config_data);

        console.log('The configuration has been successfully uploaded to s3');
        set_textbox_value_gradio('html_info_txt2img', "The configuration has been successfully uploaded.")

        // alert("The configuration has been successfully uploaded.");
        return [endpoint_value, "", ""];

    } catch (error) {
        console.error("Error in txt2img_config_save:", error);
        set_textbox_value('#html_info_txt2img', "An error occurred while uploading the configuration. error:" + error)
        return ["FAILURE", "", ""];
    }
}

async function img2img_config_save(endpoint_value, init_img, sketch, init_img_with_mask, inpaint_color_sketch, init_img_inpaint, init_mask_inpaint) {
    var config = {};
    // set_textbox_value('#html_info_img2img', "Start uploading configuration to S3, please wait ......")
    set_textbox_value_gradio('html_info_img2img', "Start uploading configuration to S3, please wait ......")

    console.log(JSON.stringify(endpoint_value))

    config["img2img_init_img"] =init_img
    config["img2img_sketch"] = sketch
    config["img2img_init_img_with_mask"] = init_img_with_mask
    config["img2img_inpaint_color_sketch"] = inpaint_color_sketch
    config["img2img_init_img_inpaint"]=init_img_inpaint;
    config['img2img_init_mask_inpaint']=init_mask_inpaint;

    scrap_ui_component_value_with_default(config);

    config['img2img_selected_tab_name'] = getSelectedButton()

    console.log(config['img2img_selected_tab_name'])

    config['img2img_selected_resize_tab'] = getSelectedTabResize()

    console.log(config['img2img_selected_resize_tab'])


    //following code is to get s3 presigned url from middleware and upload the ui parameters
    const key = "config/aigc.json";
    let remote_url = config["aws_api_gateway_url"];
    if (!remote_url.endsWith("/")) {
        remote_url += "/";
    }
    let get_presigned_s3_url = remote_url;
    get_presigned_s3_url += "inference/generate-s3-presigned-url-for-uploading";
    const api_key = config["aws_api_token"];

    try {
        const config_presigned_url = await getPresignedUrl(
            get_presigned_s3_url,
            api_key,
            key
        );
        const url = config_presigned_url.replace(/"/g, "");
        const config_data = JSON.stringify(config);
        await put_with_xmlhttprequest(url, config_data);

        console.log('The configuration has been successfully uploaded to s3');
        set_textbox_value_gradio('html_info_img2img', "The configuration has been successfully uploaded.")
        // alert("The configuration has been successfully uploaded.");
        return [endpoint_value,init_img, sketch, init_img_with_mask, inpaint_color_sketch, init_img_inpaint, init_mask_inpaint];

    } catch (error) {
        console.error("Error in img2img_config_save:", error);
        set_textbox_value('#generation_info_img2img', "An error occurred while uploading the configuration. error:" + error)
        return ["FAILURE", init_img, sketch, init_img_with_mask, inpaint_color_sketch, init_img_inpaint, init_mask_inpaint];
    }
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

async function txt2img_config_save_test(endpoint_value) {
  console.log("Before sleep");
  await sleep(5000);
  console.log("After sleep");
}

function scrap_ui_component_value_with_default(config) {
    const getElementValue = (selector, property, defaultValue) => {
        const element = document.querySelector(selector);
        return element ? element[property] : defaultValue;
    };

    config["script_txt2txt_xyz_plot_x_values"] = getElementValue(
        "#script_txt2txt_xyz_plot_x_values > label > textarea",
        "value",
        ""
    );
    config["script_txt2txt_xyz_plot_y_values"] = getElementValue(
        "#script_txt2txt_xyz_plot_y_values > label > textarea",
        "value",
        ""
    );
    config["script_txt2txt_xyz_plot_z_values"] = getElementValue(
        "#script_txt2txt_xyz_plot_z_values > label > textarea",
        "value",
        ""
    );
    config["script_txt2txt_prompt_matrix_different_seeds"] = getElementValue(
        "#script_txt2txt_prompt_matrix_different_seeds > label > input",
        "checked",
        false
    );
    config["script_txt2txt_prompt_matrix_margin_size"] = getElementValue(
        "#script_txt2txt_prompt_matrix_margin_size > div > div > input",
        "value",
        ""
    );
    config["script_txt2txt_prompt_matrix_put_at_start"] = getElementValue(
        "#script_txt2txt_prompt_matrix_put_at_start > label > input",
        "checked",
        false
    );
    config["script_txt2txt_checkbox_iterate_every_line"] =
        getElementValue(
            "#script_txt2txt_prompts_from_file_or_textbox_checkbox_iterate > label > input",
            "checked",
            false
        );
    config["script_txt2txt_checkbox_iterate_all_lines"] =
        getElementValue(
            "#script_txt2txt_prompts_from_file_or_textbox_checkbox_iterate_batch > label > input",
            "checked",
            false
        );
    config["script_txt2txt_xyz_plot_draw_legend"] = getElementValue(
        "#script_txt2txt_xyz_plot_draw_legend > label > input",
        "checked",
        false
    );
    config["script_txt2txt_xyz_plot_include_lone_images"] = getElementValue(
        "#script_txt2txt_xyz_plot_include_lone_images > label > input",
        "checked",
        false
    );
    config["script_txt2txt_xyz_plot_include_sub_grids"] = getElementValue(
        "#script_txt2txt_xyz_plot_include_sub_grids > label > input",
        "checked",
        false
    );
    config["script_txt2txt_xyz_plot_margin_size"] = getElementValue(
        "#script_txt2txt_xyz_plot_margin_size > div > div > input",
        "value",
        ""
    );
    config["script_txt2txt_xyz_plot_no_fixed_seeds"] = getElementValue(
        "#script_txt2txt_xyz_plot_no_fixed_seeds > label > input",
        "checked",
        false
    );
    config["txt2img_batch_count"] = getElementValue(
        "#txt2img_batch_count > div > div > input",
        "value",
        ""
    );
    config["txt2img_batch_size"] = getElementValue(
        "#txt2img_batch_size > div > div > input",
        "value",
        ""
    );
    config["txt2img_cfg_scale"] = getElementValue(
        "#txt2img_cfg_scale > div > div > input",
        "value",
        ""
    );
    config["txt2img_denoising_strength"] = getElementValue(
        "#txt2img_denoising_strength > div > div > input",
        "value",
        ""
    );
    config["txt2img_enable_hr"] = getElementValue(
        "#txt2img_enable_hr > label > input",
        "checked",
        false
    );
    config["txt2img_height"] = getElementValue(
        "#txt2img_height > div > div > input",
        "value",
        ""
    );
    config["txt2img_hires_steps"] = getElementValue(
        "#txt2img_hires_steps > div > div > input",
        "value",
        ""
    );
    config["txt2img_hr_resize_x"] = getElementValue(
        "#txt2img_hr_resize_x > div > div > input",
        "value",
        ""
    );
    config["txt2img_hr_resize_y"] = getElementValue(
        "#txt2img_hr_resize_y > div > div > input",
        "value",
        ""
    );
    config["txt2img_hr_scale"] = getElementValue(
        "#txt2img_hr_scale > div > div > input",
        "value",
        ""
    );
    config["txt2img_restore_faces"] = getElementValue(
        "#txt2img_restore_faces > label > input",
        "checked",
        false
    );
    config["txt2img_seed"] = getElementValue(
        "#txt2img_seed > label > input",
        "value",
        ""
    );
    config["txt2img_seed_resize_from_h"] = getElementValue(
        "#txt2img_seed_resize_from_h > div > div > input",
        "value",
        ""
    );
    config["txt2img_seed_resize_from_w"] = getElementValue(
        "#txt2img_seed_resize_from_w > div > div > input",
        "value",
        ""
    );
    
    config["txt2img_steps"] = getElementValue(
        "#txt2img_steps > div > div > input",
        "value",
        ""
    );
    config["txt2img_subseed"] = getElementValue(
        "#txt2img_subseed > label > input",
        "value",
        ""
    );
    config["txt2img_subseed_show"] = getElementValue(
        "#txt2img_subseed_show > label > input",
        "checked",
        false
    );
    config["txt2img_subseed_strength"] = getElementValue(
        "#txt2img_subseed_strength > div > div > input",
        "value",
        ""
    );
    config["txt2img_tiling"] = getElementValue(
        "#txt2img_tiling > label > input",
        "checked",
        false
    );
    config["txt2img_width"] = getElementValue(
        "#txt2img_width > div > div > input",
        "value",
        ""
    );
    
    config["script_list"] = getElementValue(
        "#script_list > label > div > div.wrap-inner.svelte-aqlk7e > div > input",
        "value",
        ""
    );
    
    config["script_txt2txt_xyz_plot_x_type"] = getElementValue(
        "#script_txt2txt_xyz_plot_x_type > label > div > div.wrap-inner.svelte-aqlk7e > div > input",
        "value",
        ""
    );
    config["script_txt2txt_xyz_plot_x_value"] = getElementValue(
        "#script_txt2txt_xyz_plot_x_values > label > textarea",
        "value",
        ""
    );
    config["script_txt2txt_xyz_plot_y_type"] = getElementValue(
        "#script_txt2txt_xyz_plot_y_type > label > div > div.wrap-inner.svelte-aqlk7e > div > input",
        "value",
        ""
    );
    config["script_txt2txt_xyz_plot_y_value"] = getElementValue(
        "#script_txt2txt_xyz_plot_y_values > label > textarea",
        "value",
        ""
    );
    config["script_txt2txt_xyz_plot_z_type"] = getElementValue(
        "#script_txt2txt_xyz_plot_z_type > label > div > div.wrap-inner.svelte-aqlk7e > div > input",
        "value",
        ""
    );
    config["script_txt2txt_xyz_plot_z_value"] = getElementValue(
        "#script_txt2txt_xyz_plot_z_values > label > textarea",
        "value",
        ""
    );
    
    config["txt2img_hr_upscaler"] = getElementValue(
        "#txt2img_hr_upscaler > label > div > div > div > input",
        "value",
        ""
    );
    config["txt2img_sampling_method"] = getElementValue(
        "#txt2img_sampling > label > div > div.wrap-inner.svelte-aqlk7e > div > input",
        "value",
        ""
    );
    
    config["txt2img_sampling_steps"] = getElementValue(
        "#txt2img_steps > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    );
    
    //sagemaker endpoint
    // config["sagemaker_endpoint"] = getElementValue(
    //     "#sagemaker_endpoint_dropdown > label > div > div.wrap-inner.svelte-aqlk7e > div > input",
    //     "value",
    //     ""
    // );
    // config["sagemaker_endpoint"] = document.querySelector("#sagemaker_endpoint_dropdown > label > div > div.wrap-inner.svelte-aqlk7e > div > input").value.split("+")[0];
    const sagemaker_ep_info = document.querySelector("#sagemaker_endpoint_dropdown > label > div > div.wrap-inner.svelte-aqlk7e > div > input").value;
    const sagemaker_ep_info_array = sagemaker_ep_info.split("+");
    config["sagemaker_endpoint"] = sagemaker_ep_info_array[0];

    //stable diffusion checkpoint
    const sd_checkpoint = document.querySelector(
        "#stable_diffusion_checkpoint_dropdown > label > div > div.wrap-inner.svelte-aqlk7e"
    );
    const sd_tokens = sd_checkpoint.querySelectorAll(".token.svelte-aqlk7e");
    const sd_values = [];
    
    sd_tokens.forEach((token) => {
        const spanValue = token.querySelector("span.svelte-aqlk7e").textContent;
        sd_values.push(spanValue);
    });
    config["sagemaker_stable_diffusion_checkpoint"] = sd_values.join(":");
    
    //Textual Inversion
    const wrapInner = document.querySelector(
        "#sagemaker_texual_inversion_dropdown > label > div > div.wrap-inner.svelte-aqlk7e"
    );
    const tokens = wrapInner.querySelectorAll(".token.svelte-aqlk7e");
    const values = [];
    
    tokens.forEach((token) => {
        const spanValue = token.querySelector("span.svelte-aqlk7e").textContent;
        values.push(spanValue);
    });
    config["sagemaker_texual_inversion_model"] = values.join(":");
    
    //LoRa
    const wrapInner1 = document.querySelector(
        "#sagemaker_lora_list_dropdown > label > div > div.wrap-inner.svelte-aqlk7e"
    );
    const tokens1 = wrapInner1.querySelectorAll(".token.svelte-aqlk7e");
    const values1 = [];
    
    tokens1.forEach((token) => {
        const spanValue = token.querySelector("span.svelte-aqlk7e").textContent;
        values1.push(spanValue);
    });
    config["sagemaker_lora_model"] = values1.join(":");
    console.log(values1);
    
    //HyperNetwork
    const wrapInner2 = document.querySelector(
        "#sagemaker_hypernetwork_dropdown > label > div > div.wrap-inner.svelte-aqlk7e"
    );
    const tokens2 = wrapInner2.querySelectorAll(".token.svelte-aqlk7e");
    const values2 = [];
    
    tokens2.forEach((token) => {
        const spanValue = token.querySelector("span.svelte-aqlk7e").textContent;
        values2.push(spanValue);
    });
    config["sagemaker_hypernetwork_model"] = values2.join(":");
    console.log(values2);
    
    //ControlNet model
    const wrapInner3 = document.querySelector(
        "#sagemaker_controlnet_model_dropdown > label > div > div.wrap-inner.svelte-aqlk7e"
    );
    const tokens3 = wrapInner3.querySelectorAll(".token.svelte-aqlk7e");
    const values3 = [];
    
    tokens3.forEach((token) => {
        const spanValue = token.querySelector("span.svelte-aqlk7e").textContent;
        values3.push(spanValue);
    });
    config["sagemaker_controlnet_model"] = values3.join(":");
    console.log(values3);
    
    //control net part parameter
    const imgElement = document.querySelector(
        "#txt2img_controlnet_ControlNet_input_image > div.image-container.svelte-p3y7hu > div > img"
    );
    if (imgElement) {
        const srcValue = imgElement.getAttribute("src");
        // Use the srcValue variable as needed
        config["txt2img_controlnet_ControlNet_input_image"] = srcValue;
    } else {
        // Handle the case when imgElement is null or undefined
        console.log("imgElement is null or undefined");
        config["txt2img_controlnet_ControlNet_input_image"] = "";
    }

    // Start grapping controlnet related ui values
    config["controlnet_enable"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_enable_checkbox > label > input",
        "checked",
        false
    );
    
    config["controlnet_lowVRAM_enable"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_low_vram_checkbox > label > input",
        "checked",
        false
    );

    config["controlnet_pixel_perfect"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_pixel_perfect_checkbox > label > input",
        "checked",
        false
    );
    
    config["controlnet_allow_preview"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_preprocessor_preview_checkbox > label > input",
        "checked",
        false
    );

    
    config["controlnet_preprocessor"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_preprocessor_dropdown > label > div > div.wrap-inner.svelte-aqlk7e > div > input",
        "value",
        ""
    );

    config["controlnet_model"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_model_dropdown > label > div > div.wrap-inner.svelte-aqlk7e > div > input",
        "value",
        ""
    );

    config["controlnet_weight"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_control_weight_slider > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    );

    config["controlnet_starting_control_step"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_start_control_step_slider > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    );

    config["controlnet_ending_control_step"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_ending_control_step_slider > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    );

    config["controlnet_control_mode_balanced"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_control_mode_radio > div.wrap.svelte-1p9xokt > label:nth-child(1) > input",
        "checked",
        false 
    );

    config["controlnet_control_mode_my_prompt_is_more_important"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_control_mode_radio > div.wrap.svelte-1p9xokt > label:nth-child(2) > input",
        "checked",
        false 
    );

    config["controlnet_control_mode_controlnet_is_more_important"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_control_mode_radio > div.wrap.svelte-1p9xokt > label:nth-child(3) > input",
        "checked",
        false 
    );

    config["controlnet_resize_mode_just_resize"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_resize_mode_radio > div.wrap.svelte-1p9xokt > label:nth-child(1) > input",
        "checked",
        false 
    );

    config["controlnet_resize_mode_Crop_and_Resize"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_resize_mode_radio > div.wrap.svelte-1p9xokt > label:nth-child(2) > input",
        "checked",
        false 
    );

    config["controlnet_resize_mode_Resize_and_Fill"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_resize_mode_radio > div.wrap.svelte-1p9xokt > label:nth-child(3) > input",
        "checked",
        false 
    );

    config[
        "controlnet_loopback_automatically"
    ] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_automatically_send_generated_images_checkbox > label > input",
        "checked", 
        false
    );
    

    // Completed when Preprocessor is null

    // Start when Preprocessor is canny
    config["controlnet_preprocessor_resolution"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_preprocessor_resolution_slider> div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    )

    config["controlnet_canny_low_threshold"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_threshold_A_slider> div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    )

    config["controlnet_canny_high_threshold"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_threshold_B_slider> div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    ) 

    // end of controlnet section
    
    config["script_txt2txt_prompt_matrix_prompt_type_positive"] = getElementValue(
        "#script_txt2txt_prompt_matrix_prompt_type > div.wrap.svelte-1p9xokt > label.svelte-1p9xokt.selected > input",
        "checked",
        false
    );
    config["script_txt2txt_prompt_matrix_prompt_type_negative"] = getElementValue(
        "#script_txt2txt_prompt_matrix_prompt_type > div.wrap.svelte-1p9xokt > label:nth-child(2) > input",
        "checked",
        false
    );
    config["script_txt2txt_prompt_matrix_variations_delimiter_comma"] =
        getElementValue(
            "#script_txt2txt_prompt_matrix_variations_delimiter > div.wrap.svelte-1p9xokt > label.svelte-1p9xokt.selected > input",
            "checked",
            false
        );
    config["script_txt2txt_prompt_matrix_variations_delimiter_space"] =
        getElementValue(
            "#script_txt2txt_prompt_matrix_variations_delimiter > div.wrap.svelte-1p9xokt > label:nth-child(2) > input",
            "checked",
            false
        );
    config["script_txt2txt_prompt_matrix_margin_size"] = getElementValue(
        "#script_txt2txt_prompt_matrix_margin_size > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    );
    
    config["script_txt2txt_prompts_from_file_or_textbox_checkbox_iterate"] =
        getElementValue(
            "#script_txt2txt_prompts_from_file_or_textbox_checkbox_iterate > label > input",
            "enabled",
            false
        );
    config["script_txt2txt_prompts_from_file_or_textbox_checkbox_iterate_batch"] =
        getElementValue(
            "#script_txt2txt_prompts_from_file_or_textbox_checkbox_iterate_batch > label > input",
            "enabled",
            false 
        );
    config["script_txt2txt_prompts_from_file_or_textbox_prompt_txt"] =
        getElementValue(
            "#script_txt2txt_prompts_from_file_or_textbox_prompt_txt > label > textarea",
            "value",
            ""
        );
    config["script_txt2txt_prompts_from_file_or_textbox_file"] = getElementValue(
        "#script_txt2txt_prompts_from_file_or_textbox_file > div.svelte-116rqfv.center.boundedheight.flex > div",
        "value",
        ""
    );
    
    // config for prompt area
    config["txt2img_prompt"] = getElementValue(
        "#txt2img_prompt > label > textarea",
        "value",
        ""
    );
    config["txt2img_neg_prompt"] = getElementValue(
        "#txt2img_neg_prompt > label > textarea",
        "value",
        ""
    );
    config["txt2img_styles"] = getElementValue(
        "#txt2img_styles > label > div > div > div > input",
        "value",
        ""
    );
    
    // get the api-gateway url and token
    config["aws_api_gateway_url"] = getElementValue(
        "#aws_middleware_api > label > textarea",
        "value",
        ""
    );
    
    config["aws_api_token"] = getElementValue(
        "#aws_middleware_token > label > textarea",
        "value",
        ""
    );

    // get the img2img component

    //document.querySelector("#img2img_prompt > label > textarea")
    config["img2img_prompt"] = getElementValue(
        "#img2img_prompt > label > textarea",
        "value",
        ""
    );

    // document.querySelector("#img2img_neg_prompt > label > textarea")
    config["img2img_neg_prompt"] = getElementValue(
        "#img2img_neg_prompt > label > textarea",
        "value",
        ""
    )
    // document.querySelector("#img2img_styles > label > div > div.wrap-inner.svelte-aqlk7e > div > input")
    config["img2img_styles"] = getElementValue(
        "#img2img_styles > label > div > div.wrap-inner.svelte-aqlk7e > div > input",
        "value",
        ""
    )

    
    // Resize mode
    // document.querySelector("#resize_mode > div.wrap.svelte-1p9xokt > label.svelte-1p9xokt.selected > input")
    config["img2img_resize_mode_just_resize"] = getElementValue(
        "#resize_mode > div.wrap.svelte-1p9xokt > label.svelte-1p9xokt.selected > input",
        "checked",
        false
    );
    // document.querySelector("#resize_mode > div.wrap.svelte-1p9xokt > label:nth-child(2) > input")
    config["img2img_resize_mode_crop_and_resize"] = getElementValue(
        "#resize_mode > div.wrap.svelte-1p9xokt > label:nth-child(2) > input",
        "checked",
        false
    );

    // document.querySelector("#resize_mode > div.wrap.svelte-1p9xokt > label:nth-child(3) > input")
    config["img2img_resize_mode_resize_and_fill"] = getElementValue(
        "#resize_mode > div.wrap.svelte-1p9xokt > label:nth-child(3) > input",
        "checked",
        false
    );
    // document.querySelector("#resize_mode > div.wrap.svelte-1p9xokt > label:nth-child(4) > input")
    config["img2img_resize_mode_just_resize_latent_upscale"] = getElementValue(
        "#resize_mode > div.wrap.svelte-1p9xokt > label:nth-child(4) > input",
        "checked",
        false
    );
    
    // img2img sampling method
    // document.querySelector("#img2img_sampling > label > div > div.wrap-inner.svelte-aqlk7e > div > input")
    config["img2img_sampling_method"] = getElementValue(
        "#img2img_sampling > label > div > div.wrap-inner.svelte-aqlk7e > div > input",
        "value",
        ""
    );
    
    // document.querySelector("#img2img_steps > div.wrap.svelte-1cl284s > div > input")
    config["img2img_sampling_steps"] = getElementValue(
        "#img2img_steps > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    );

    // document.querySelector("#img2img_restore_faces > label > input")
    config["img2img_restore_faces"] = getElementValue(
        "#img2img_restore_faces > label > input",
        "checked",
        false
    );

    // document.querySelector("#img2img_tiling > label > input")
    config["img2img_tiling"] = getElementValue(
        "#img2img_tiling > label > input",
        "checked",
        false
    );

    // Resize to
    // document.querySelector("#img2img_width > div.wrap.svelte-1cl284s > div > input")
    config["img2img_width"] = getElementValue(
        "#img2img_width > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    );

    // document.querySelector("#img2img_height > div.wrap.svelte-1cl284s > div > input")
    config["img2img_height"] = getElementValue(
        "#img2img_height > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    );

    // document.querySelector("#img2img_batch_count > div.wrap.svelte-1cl284s > div > input")
    config["img2img_batch_count"] = getElementValue(
        "#img2img_batch_count > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    ); 

    // document.querySelector("#img2img_batch_size > div.wrap.svelte-1cl284s > div > input")
    config["img2img_batch_size"] = getElementValue(
        "#img2img_batch_size > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    ); 

    // document.querySelector("#img2img_cfg_scale > div.wrap.svelte-1cl284s > div > input")
    config["img2img_cfg_scale"] = getElementValue(
        "#img2img_cfg_scale > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    ); 

    // document.querySelector("#img2img_denoising_strength > div.wrap.svelte-1cl284s > div > input")
    config["img2img_denoising_strength"] = getElementValue(
        "#img2img_denoising_strength > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    ); 

    // document.querySelector("#img2img_seed > label > input")
    config["img2img_seed"] = getElementValue(
        "#img2img_seed > label > input",
        "value",
        ""
    ); 

    // document.querySelector("#img2img_subseed_show > label > input")
    config["img2img_subseed_show"] = getElementValue(
        "#img2img_subseed_show > label > input",
        "checked",
        false
    );

    // document.querySelector("#img2img_subseed > label > input")
    config["img2img_subseed"] = getElementValue(
        "#img2img_subseed > label > input",
        "value",
        ""
    ); 
    // document.querySelector("#img2img_subseed_strength > div.wrap.svelte-1cl284s > div > input")
    config["img2img_subseed_strength"] = getElementValue(
        "#img2img_subseed_strength > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    ); 

    // document.querySelector("#img2img_seed_resize_from_w > div.wrap.svelte-1cl284s > div > input")
    config["img2img_seed_resize_from_w"] = getElementValue(
        "#img2img_seed_resize_from_w > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    ); 

    // document.querySelector("#img2img_seed_resize_from_h > div.wrap.svelte-1cl284s > div > input")
    config["img2img_seed_resize_from_h"] = getElementValue(
        "#img2img_seed_resize_from_h > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    ); 


    // Resize by
    // document.querySelector("#img2img_scale > div.wrap.svelte-1cl284s > div > input")
    config["img2img_scale"] = getElementValue(
        "#img2img_scale > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    ); 

    // inpaint component
   
    // document.querySelector("#img2img_mask_blur > div.wrap.svelte-1cl284s > div > input")
    config["img2img_mask_blur"] = getElementValue(
        "#img2img_mask_blur > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    ); 

    // document.querySelector("#img2img_mask_mode > div.wrap.svelte-1p9xokt > label.svelte-1p9xokt.selected > input")
    config["img2img_mask_mode_inpaint_masked"] = getElementValue(
        "#img2img_mask_mode > div.wrap.svelte-1p9xokt > label:nth-child(1) > input",
        "checked",
        false
    );

    // document.querySelector("#img2img_mask_mode > div.wrap.svelte-1p9xokt > label:nth-child(2) > input")
    config["img2img_mask_mode_inpaint_not_masked"] = getElementValue(
        "#img2img_mask_mode > div.wrap.svelte-1p9xokt > label:nth-child(2) > input",
        "checked",
        false
    );

    // document.querySelector("#img2img_inpainting_fill > div.wrap.svelte-1p9xokt > label:nth-child(1) > input")
    config["img2img_inpainting_fill_fill"] = getElementValue(
        "#img2img_inpainting_fill > div.wrap.svelte-1p9xokt > label:nth-child(1) > input",
        "checked",
        false
    );


    // document.querySelector("#img2img_inpainting_fill > div.wrap.svelte-1p9xokt > label:nth-child(2) > input")
    config["img2img_inpainting_fill_original"] = getElementValue(
        "#img2img_inpainting_fill > div.wrap.svelte-1p9xokt > label:nth-child(2) > input",
        "checked",
        false
    );

    // document.querySelector("#resize_mode > div.wrap.svelte-1p9xokt > label:nth-child(3) > input")
    config["img2img_inpainting_fill_latent_noise"] = getElementValue(
        "#img2img_inpainting_fill > div.wrap.svelte-1p9xokt > label:nth-child(3) > input",
        "checked",
        false
    );

    // document.querySelector("#resize_mode > div.wrap.svelte-1p9xokt > label:nth-child(4) > input")
    config["img2img_inpainting_fill_latent_nothing"] = getElementValue(
        "#img2img_inpainting_fill > div.wrap.sverte-1p9xokt > label:nth-child(4) > input",
        "checked",
        false
    );

    // document.querySelector("#img2img_inpaint_full_res > div.wrap.svelte-1p9xokt > label:nth-child(1) > input")
    config["img2img_inpaint_full_res_whole_picture"] = getElementValue(
        "#img2img_inpaint_full_res > div.wrap.svelte-1p9xokt > label:nth-child(1) > input",
        "checked",
        false
    );

    // document.querySelector("#img2img_inpaint_full_res > div.wrap.svelte-1p9xokt > label:nth-child(2) > input")
    config["img2img_inpaint_full_res_only_masked"] = getElementValue(
        "#img2img_inpaint_full_res > div.wrap.svelte-1p9xokt > label:nth-child(2) > input",
        "checked",
        false
    );

    // document.querySelector("#img2img_steps > div.wrap.svelte-1cl284s > div > input")
    config["img2img_steps"] = getElementValue(
        "#img2img_steps > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    ); 

    // grab the img2img inpaint sketch original image
    //document.querySelector("#inpaint_sketch")
    const inpaintImgElement = document.querySelector(
        "#inpaint_sketch > div.image-container.svelte-p3y7hu > div > img"
    );
    if (inpaintImgElement) {
        const srcValue = inpaintImgElement.getAttribute("src");
        // Use the srcValue variable as needed
        config["img2img_inpaint_sketch_image"] = srcValue;
    } else {
        // Handle the case when imgElement is null or undefined
        console.log("inpaintImgElement is null or undefined");
        config["img2img_inpaint_sketch_image"] = "";
    }



    // end of img2img component
    

    



}

function put_with_xmlhttprequest(config_url, config_data) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("PUT", config_url, true);

        xhr.onreadystatechange = () => {
            if (xhr.readyState === 4) {
                // Print all response headers to the console
                console.log(xhr.getAllResponseHeaders());

                if (xhr.status >= 200 && xhr.status < 300) {
                    resolve(xhr.responseText);
                } else {
                    reject(xhr.statusText);
                }
            }
        };

        xhr.onerror = () => {
            // Print all response headers to the console
            console.log(xhr.getAllResponseHeaders());
            reject("Network error");
        };

        xhr.send(config_data);
    });
}


function getPresignedUrl(remote_url, api_key, key) {
    return new Promise((resolve, reject) => {
        const apiUrl = remote_url;
        const queryParams = new URLSearchParams({
            key: key,
        });

        const xhr = new XMLHttpRequest();
        xhr.open("GET", `${apiUrl}?${queryParams}`, true);
        xhr.setRequestHeader("x-api-key", api_key);

        xhr.onload = function () {
            if (xhr.status >= 200 && xhr.status < 400) {
                resolve(xhr.responseText);
            } else {
                reject(
                    new Error(`Error fetching presigned URL: ${xhr.statusText}`)
                );
            }
        };

        xhr.onerror = function () {
            reject(new Error("Error fetching presigned URL"));
        };

        xhr.send();
    });
}

function postToApiGateway(remote_url, api_key, data, callback) {
    const apiUrl = remote_url;

    const xhr = new XMLHttpRequest();
    xhr.open("POST", apiUrl, true);
    // xhr.setRequestHeader("Content-Type", "application/json");
    xhr.setRequestHeader("x-api-key", api_key);

    xhr.onload = function () {
        if (xhr.status >= 200 && xhr.status < 400) {
            callback(null, xhr.responseText);
        } else {
            callback(
                new Error(`Error posting to API Gateway: ${xhr.statusText}`),
                null
            );
        }
    };

    xhr.onerror = function () {
        callback(new Error("Error posting to API Gateway"), null);
    };

    // Convert data object to JSON string before sending
    xhr.send(JSON.stringify(data));
}
