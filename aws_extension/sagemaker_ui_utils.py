import gradio
import gradio as gr
import threading
import time
from aws_extension import sagemaker_ui
from modules.ui_components import ToolButton
from aws_extension.constant import MODEL_TYPE

training_job_dashboard = None
txt2img_show_hook = None
txt2img_lora_show_hook = None
txt2img_hypernet_show_hook = None
txt2img_embedding_show_hook = None
img2img_prompt = None
img2img_lora_show_hook = None
img2img_hypernet_show_hook = None
img2img_embedding_show_hook = None
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


last_warning_time = None
warning_lock = threading.Lock()


def warning(msg, seconds: int = 3600):
    global last_warning_time
    with warning_lock:
        current_time = time.time()
        if last_warning_time is None or current_time - last_warning_time > seconds:
            last_warning_time = current_time
            gr.Warning(msg)


def on_after_component_callback(component, **_kwargs):
    global db_model_name, db_use_txt2img, db_sagemaker_train, db_save_config, cloud_db_model_name, \
        cloud_train_instance_type, training_job_dashboard
    # Hook image display logic
    global txt2img_gallery, txt2img_generation_info, txt2img_html_info, \
        txt2img_show_hook, txt2img_prompt, txt2img_lora_show_hook, \
            txt2img_hypernet_show_hook, txt2img_embedding_show_hook
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
    if sagemaker_ui.inference_job_dropdown is not None and \
            txt2img_gallery is not None and \
            txt2img_generation_info is not None and \
            txt2img_html_info is not None and \
            txt2img_show_hook is None and \
            txt2img_prompt is not None:
        txt2img_show_hook = "finish"
        sagemaker_ui.inference_job_dropdown.change(
            fn=sagemaker_ui.fake_gan,
            inputs=[sagemaker_ui.inference_job_dropdown, txt2img_prompt],
            outputs=[txt2img_gallery, txt2img_generation_info, txt2img_html_info, txt2img_prompt]
        )

    if sagemaker_ui.lora_dropdown is not None and \
            txt2img_lora_show_hook is None and \
            txt2img_prompt is not None:
        txt2img_lora_show_hook = "finish"
        sagemaker_ui.lora_dropdown.change(
            fn=sagemaker_ui.update_prompt_with_lora,
            inputs=[sagemaker_ui.lora_dropdown, txt2img_prompt],
            outputs=[txt2img_prompt]
        )
        sagemaker_ui.lora_dropdown = None

    if sagemaker_ui.hypernet_dropdown is not None and \
            txt2img_hypernet_show_hook is None and \
            txt2img_prompt is not None:
        txt2img_hypernet_show_hook = "finish"
        sagemaker_ui.hypernet_dropdown.change(
            fn=sagemaker_ui.update_prompt_with_hypernetwork,
            inputs=[sagemaker_ui.hypernet_dropdown, txt2img_prompt],
            outputs=[txt2img_prompt]
        )
        sagemaker_ui.hypernet_dropdown = None

    if sagemaker_ui.embedding_dropdown is not None and \
            txt2img_embedding_show_hook is None and \
            txt2img_prompt is not None:
        txt2img_embedding_show_hook = "finish"
        sagemaker_ui.embedding_dropdown.change(
            fn=sagemaker_ui.update_prompt_with_embedding,
            inputs=[sagemaker_ui.embedding_dropdown, txt2img_prompt, sagemaker_ui.lora_and_hypernet_models_state],
            outputs=[txt2img_prompt]
        )
        sagemaker_ui.embedding_dropdown = None

    global img2img_gallery, img2img_generation_info, img2img_html_info, img2img_show_hook, \
        img2img_prompt, \
        init_img, \
        sketch, \
        init_img_with_mask, \
        inpaint_color_sketch, \
        init_img_inpaint, \
        init_mask_inpaint, \
        img2img_lora_show_hook, \
        img2img_hypernet_show_hook, \
        img2img_embedding_show_hook
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

    if sagemaker_ui.inference_job_dropdown is not None and \
            img2img_gallery is not None and \
            img2img_generation_info is not None and \
            img2img_html_info is not None and \
            img2img_show_hook is None and \
            img2img_prompt is not None:

        img2img_show_hook = "finish"
        sagemaker_ui.inference_job_dropdown.change(
            fn=sagemaker_ui.fake_gan,
            inputs=[sagemaker_ui.inference_job_dropdown, img2img_prompt],
            outputs=[img2img_gallery, img2img_generation_info, img2img_html_info, img2img_prompt]
        )

    if sagemaker_ui.lora_dropdown is not None and \
            img2img_lora_show_hook is None and \
            img2img_prompt is not None:
        img2img_lora_show_hook = "finish"
        sagemaker_ui.lora_dropdown.change(
            fn=sagemaker_ui.update_prompt_with_lora,
            inputs=[sagemaker_ui.lora_dropdown, img2img_prompt],
            outputs=[img2img_prompt]
        )
        sagemaker_ui.lora_dropdown = None

    if sagemaker_ui.hypernet_dropdown is not None and \
            img2img_hypernet_show_hook is None and \
            img2img_prompt is not None:
        img2img_hypernet_show_hook = "finish"
        sagemaker_ui.hypernet_dropdown.change(
            fn=sagemaker_ui.update_prompt_with_hypernetwork,
            inputs=[sagemaker_ui.hypernet_dropdown, img2img_prompt],
            outputs=[img2img_prompt]
        )
        sagemaker_ui.hypernet_dropdown = None

    if sagemaker_ui.embedding_dropdown is not None and \
            img2img_embedding_show_hook is None and \
            img2img_prompt is not None:
        img2img_embedding_show_hook = "finish"
        sagemaker_ui.embedding_dropdown.change(
            fn=sagemaker_ui.update_prompt_with_embedding,
            inputs=[sagemaker_ui.embedding_dropdown, img2img_prompt, sagemaker_ui.lora_and_hypernet_models_state],
            outputs=[img2img_prompt]
        )
        sagemaker_ui.embedding_dropdown = None

def create_refresh_button_by_user(refresh_component, refresh_method, refreshed_args, elem_id):
    def refresh(pr: gradio.Request):
        refresh_method(pr.username)
        args = refreshed_args(pr.username) if callable(refreshed_args) else refreshed_args

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
