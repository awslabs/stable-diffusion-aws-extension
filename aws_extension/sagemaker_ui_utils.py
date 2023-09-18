import gradio
import gradio as gr

from aws_extension import sagemaker_ui
from dreambooth_on_cloud.train import async_cloud_train
from modules.ui_components import ToolButton

training_job_dashboard = None
txt2img_show_hook = None
img2img_prompt = None
init_img = None
sketch = None
init_img_with_mask = None
inpaint_color_sketch = None
init_img_inpaint = None
init_mask_inpaint = None
img2img_gallery = None
img2img_show_hook = None
img2img_generation_info = None
txt2img_generation_info = None
txt2img_gallery = None
img2img_html_info = None
db_model_name = None
db_use_txt2img = None
db_sagemaker_train = None
db_save_config = None
cloud_db_model_name = None
cloud_train_instance_type = None
txt2img_html_info = None
txt2img_prompt = None


def on_after_component_callback(component, **_kwargs):
    global db_model_name, db_use_txt2img, db_sagemaker_train, db_save_config, cloud_db_model_name, \
        cloud_train_instance_type, training_job_dashboard

    is_dreambooth_train = type(component) is gr.Button and getattr(component, 'elem_id', None) == 'db_train'
    is_dreambooth_model_name = type(component) is gr.Dropdown and \
        (getattr(component, 'elem_id', None) == 'model_name' or
         (getattr(component, 'label', None) == 'Model' and getattr(
            component.parent.parent.parent.parent, 'elem_id', None) == 'ModelPanel'))
    is_cloud_dreambooth_model_name = type(component) is gr.Dropdown and \
        getattr(component, 'elem_id', None) == 'cloud_db_model_name'
    is_machine_type_for_train = type(component) is gr.Dropdown and \
        getattr(component, 'elem_id', None) == 'cloud_train_instance_type'
    is_dreambooth_use_txt2img = type(component) is gr.Checkbox and getattr(component, 'label', None) == 'Use txt2img'
    is_training_job_dashboard = type(component) is gr.Dataframe and getattr(component, 'elem_id',
                                                                            None) == 'training_job_dashboard'
    is_db_save_config = getattr(component, 'elem_id', None) == 'db_save_config'
    if is_dreambooth_train:
        db_sagemaker_train = gr.Button(value="SageMaker Train", elem_id="db_sagemaker_train", variant='primary')
    if is_dreambooth_model_name:
        db_model_name = component
    if is_cloud_dreambooth_model_name:
        cloud_db_model_name = component
    if is_training_job_dashboard:
        training_job_dashboard = component
    if is_machine_type_for_train:
        cloud_train_instance_type = component
    if is_dreambooth_use_txt2img:
        db_use_txt2img = component
    if is_db_save_config:
        db_save_config = component
    # After all requiment comment is loaded, add the SageMaker training button click callback function.
    if training_job_dashboard is not None and cloud_train_instance_type is not None and \
            cloud_db_model_name is not None and db_model_name is not None and \
            db_use_txt2img is not None and db_sagemaker_train is not None and \
            (
                    is_dreambooth_train or is_dreambooth_model_name or is_dreambooth_use_txt2img
                    or is_cloud_dreambooth_model_name or is_machine_type_for_train or is_training_job_dashboard):
        db_model_name.value = "dummy_local_model"
        db_sagemaker_train.click(
            fn=async_cloud_train,
            _js="db_start_sagemaker_train",
            inputs=[
                db_model_name,
                cloud_db_model_name,
                db_use_txt2img,
                cloud_train_instance_type
            ],
            outputs=[training_job_dashboard]
        )
    # Hook image display logic
    global txt2img_gallery, txt2img_generation_info, txt2img_html_info, txt2img_show_hook, txt2img_prompt
    is_txt2img_gallery = type(component) is gr.Gallery and getattr(component, 'elem_id', None) == 'txt2img_gallery'
    is_txt2img_generation_info = type(component) is gr.Textbox and getattr(component, 'elem_id',
                                                                           None) == 'generation_info_txt2img'
    is_txt2img_html_info = type(component) is gr.HTML and getattr(component, 'elem_id', None) == 'html_info_txt2img'
    is_txt2img_prompt = type(component) is gr.Textbox and getattr(component, 'elem_id', None) == 'txt2img_prompt'
    if is_txt2img_prompt:
        txt2img_prompt = component
    if is_txt2img_gallery:
        txt2img_gallery = component
    if is_txt2img_generation_info:
        txt2img_generation_info = component
    if is_txt2img_html_info:
        txt2img_html_info = component
        # return test

        # sagemaker_ui.textual_inversion_dropdown is not None and \
        # sagemaker_ui.hyperNetwork_dropdown is not None and \
        # sagemaker_ui.lora_dropdown is not None and \
    if sagemaker_ui.inference_job_dropdown is not None and \
            txt2img_gallery is not None and \
            txt2img_generation_info is not None and \
            txt2img_html_info is not None and \
            txt2img_show_hook is None and \
            txt2img_prompt is not None:
        txt2img_show_hook = "finish"
        sagemaker_ui.inference_job_dropdown.change(
            # fn=lambda selected_value: sagemaker_ui.fake_gan(selected_value, txt2img_prompt['value']),
            fn=sagemaker_ui.fake_gan,
            inputs=[sagemaker_ui.inference_job_dropdown, txt2img_prompt],
            outputs=[txt2img_gallery, txt2img_generation_info, txt2img_html_info, txt2img_prompt]
        )

        # fixme: not sure what is this for?
        # sagemaker_ui.sagemaker_endpoint.change(
        #     fn=lambda selected_value: sagemaker_ui.displayEndpointInfo(selected_value),
        #     inputs=[sagemaker_ui.sagemaker_endpoint],
        #     outputs=[txt2img_html_info]
        # )
        # sagemaker_ui.modelmerger_merge_on_cloud.click(
        #     fn=sagemaker_ui.modelmerger_on_cloud_func,
        #     # fn=None,
        #     # _js="txt2img_config_save",
        #     inputs=[sagemaker_ui.sagemaker_endpoint],
        #     outputs=[
        #     ])
        # Hook image display logic
    global img2img_gallery, img2img_generation_info, img2img_html_info, img2img_show_hook, \
        img2img_prompt, \
        init_img, \
        sketch, \
        init_img_with_mask, \
        inpaint_color_sketch, \
        init_img_inpaint, \
        init_mask_inpaint
    is_img2img_gallery = type(component) is gr.Gallery and getattr(component, 'elem_id', None) == 'img2img_gallery'
    is_img2img_generation_info = type(component) is gr.Textbox and getattr(component, 'elem_id',
                                                                           None) == 'generation_info_img2img'
    is_img2img_html_info = type(component) is gr.HTML and getattr(component, 'elem_id', None) == 'html_info_img2img'

    is_img2img_prompt = type(component) is gr.Textbox and getattr(component, 'elem_id', None) == 'img2img_prompt'
    is_init_img = type(component) is gr.Image and getattr(component, 'elem_id', None) == 'img2img_image'
    is_sketch = type(component) is gr.Image and getattr(component, 'elem_id', None) == 'img2img_sketch'
    is_init_img_with_mask = type(component) is gr.Image and getattr(component, 'elem_id', None) == 'img2maskimg'
    is_inpaint_color_sketch = type(component) is gr.Image and getattr(component, 'elem_id', None) == 'inpaint_sketch'

    is_init_img_inpaint = type(component) is gr.Image and getattr(component, 'elem_id', None) == 'img_inpaint_base'
    is_init_mask_inpaint = type(component) is gr.Image and getattr(component, 'elem_id', None) == 'img_inpaint_mask'

    if is_img2img_gallery:
        img2img_gallery = component
    if is_img2img_generation_info:
        img2img_generation_info = component
    if is_img2img_html_info:
        img2img_html_info = component

    if is_img2img_prompt:
        img2img_prompt = component
    if is_init_img:
        init_img = component
    if is_sketch:
        sketch = component
    if is_init_img_with_mask:
        init_img_with_mask = component
    if is_inpaint_color_sketch:
        inpaint_color_sketch = component
    if is_init_img_inpaint:
        init_img_inpaint = component
    if is_init_mask_inpaint:
        init_mask_inpaint = component

    # sagemaker_ui.textual_inversion_dropdown is not None and \
    # sagemaker_ui.hyperNetwork_dropdown is not None and \
    # sagemaker_ui.lora_dropdown is not None and \
    if sagemaker_ui.inference_job_dropdown is not None and \
            img2img_gallery is not None and \
            img2img_generation_info is not None and \
            img2img_html_info is not None and \
            img2img_show_hook is None and \
            sagemaker_ui.interrogate_clip_on_cloud_button is not None and \
            sagemaker_ui.interrogate_deep_booru_on_cloud_button is not None and \
            img2img_prompt is not None and \
            init_img is not None and \
            sketch is not None and \
            init_img_with_mask is not None and \
            inpaint_color_sketch is not None and \
            init_img_inpaint is not None and \
            init_mask_inpaint is not None:
        img2img_show_hook = "finish"
        sagemaker_ui.inference_job_dropdown.change(
            fn=sagemaker_ui.fake_gan,
            inputs=[sagemaker_ui.inference_job_dropdown, img2img_prompt],
            outputs=[img2img_gallery, img2img_generation_info, img2img_html_info, img2img_prompt]
        )

        # fixme: no need to select endpoint
        # sagemaker_ui.interrogate_clip_on_cloud_button.click(
        #     fn=sagemaker_ui.call_interrogate_clip,
        #     _js="img2img_config_save",
        #     inputs=[sagemaker_ui.sagemaker_endpoint, init_img, sketch, init_img_with_mask, inpaint_color_sketch,
        #             init_img_inpaint, init_mask_inpaint],
        #     outputs=[img2img_gallery, img2img_generation_info, img2img_html_info, img2img_prompt]
        # )
        #
        # sagemaker_ui.interrogate_deep_booru_on_cloud_button.click(
        #     fn=sagemaker_ui.call_interrogate_deepbooru,
        #     _js="img2img_config_save",
        #     inputs=[sagemaker_ui.sagemaker_endpoint, init_img, sketch, init_img_with_mask, inpaint_color_sketch,
        #             init_img_inpaint, init_mask_inpaint],
        #     outputs=[img2img_gallery, img2img_generation_info, img2img_html_info, img2img_prompt]
        # )


def create_refresh_button(refresh_component, refresh_method, refreshed_args, elem_id):
    def refresh(pr: gradio.Request):
        refresh_method(pr.username)
        args = refreshed_args() if callable(refreshed_args) else refreshed_args

        for k, v in args.items():
            setattr(refresh_component, k, v)

        return gr.update(**(args or {}))

    refresh_symbol = '\U0001f504'  # 🔄
    refresh_button = ToolButton(value=refresh_symbol, elem_id=elem_id)
    refresh_button.click(
        fn=refresh,
        inputs=[],
        outputs=[refresh_component]
    )

    return refresh_button
