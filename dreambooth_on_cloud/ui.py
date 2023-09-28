import gradio as gr

from dreambooth_on_cloud.create_model import get_sd_cloud_models, get_create_model_job_list, cloud_create_model
from dreambooth_on_cloud.train import get_cloud_db_model_name_list, get_train_job_list, wrap_load_model_params
from modules import script_callbacks

# create new tabs for create Model
from modules.ui_common import create_refresh_button

origin_callback = script_callbacks.ui_tabs_callback


def avoid_duplicate_from_restart_ui(res):
    for extension_ui in res:
        if extension_ui[1] == 'Dreambooth':
            for key in list(extension_ui[0].blocks):
                val = extension_ui[0].blocks[key]
                if type(val) is gr.Tab:
                    if val.label == 'Select From Cloud':
                        return True

    return False


def get_sorted_lora_cloud_models():
    return []


def get_cloud_model_snapshots():
    return []


def ui_tabs_callback():
    res = origin_callback()
    if avoid_duplicate_from_restart_ui(res):
        return res
    for extension_ui in res:
        if extension_ui[1] == 'Dreambooth':
            for key in list(extension_ui[0].blocks):
                val = extension_ui[0].blocks[key]
                if type(val) is gr.Tab:
                    if val.label == 'Select':
                        with extension_ui[0]:
                            with val.parent:
                                with gr.Tab('Select From Cloud'):
                                    with gr.Row():
                                        cloud_db_model_name = gr.Dropdown(
                                            label="Model", choices=sorted(get_cloud_db_model_name_list()),
                                            elem_id="cloud_db_model_name"
                                        )
                                        create_refresh_button(
                                            cloud_db_model_name,
                                            get_cloud_db_model_name_list,
                                            lambda: {"choices": sorted(get_cloud_db_model_name_list())},
                                            "refresh_db_models",
                                        )
                                    with gr.Row():
                                        cloud_db_snapshot = gr.Dropdown(
                                            label="Cloud Snapshot to Resume",
                                            choices=sorted(get_cloud_model_snapshots()),
                                            elem_id="cloud_snapshot_to_resume_dropdown"
                                        )
                                        create_refresh_button(
                                            cloud_db_snapshot,
                                            get_cloud_model_snapshots,
                                            lambda: {"choices": sorted(get_cloud_model_snapshots())},
                                            "refresh_db_snapshots",
                                        )

                                    with gr.Row():
                                        cloud_train_instance_type = gr.Dropdown(
                                            label="SageMaker Train Instance Type",
                                            choices=['ml.g4dn.2xlarge', 'ml.g5.2xlarge'],
                                            elem_id="cloud_train_instance_type",
                                            info='select SageMaker Train Instance Type'
                                        )
                                    with gr.Row(visible=False) as lora_model_row:
                                        cloud_db_lora_model_name = gr.Dropdown(
                                            label="Lora Model", choices=get_sorted_lora_cloud_models(),
                                            elem_id="cloud_lora_model_dropdown"
                                        )
                                        create_refresh_button(
                                            cloud_db_lora_model_name,
                                            get_sorted_lora_cloud_models,
                                            lambda: {"choices": get_sorted_lora_cloud_models()},
                                            "refresh_lora_models",
                                        )
                                    with gr.Row():
                                        gr.HTML(value="Loaded Model from Cloud:")
                                        cloud_db_model_path = gr.HTML()
                                    with gr.Row():
                                        gr.HTML(value="Cloud Model Revision:")
                                        cloud_db_revision = gr.HTML(elem_id="cloud_db_revision")
                                    with gr.Row():
                                        gr.HTML(value="Cloud Model Epoch:")
                                        cloud_db_epochs = gr.HTML(elem_id="cloud_db_epochs")
                                    with gr.Row():
                                        gr.HTML(value="V2 Model From Cloud:")
                                        cloud_db_v2 = gr.HTML(elem_id="cloud_db_v2")
                                    with gr.Row():
                                        gr.HTML(value="Has EMA:")
                                        cloud_db_has_ema = gr.HTML(elem_id="cloud_db_has_ema")
                                    with gr.Row():
                                        gr.HTML(value="Source Checkpoint From Cloud:")
                                        cloud_db_src = gr.HTML()
                                    with gr.Row():
                                        gr.HTML(value="Cloud DB Status:")
                                        cloud_db_status = gr.HTML(elem_id="db_status", value="")
                                    with gr.Row():
                                        gr.HTML(value="Experimental Shared Source:")
                                        cloud_db_shared_diffusers_path = gr.HTML()
                                    with gr.Row():
                                        gr.HTML(value="<b>Training Jobs Details:<b/>")
                                    with gr.Row():
                                        training_job_dashboard = gr.Dataframe(
                                            headers=["id", "model name", "status", "SageMaker train name"],
                                            datatype=["str", "str", "str", "str"],
                                            col_count=(4, "fixed"),
                                            value=get_train_job_list,
                                            interactive=False,
                                            every=3,
                                            elem_id='training_job_dashboard'
                                            # show_progress=True
                                        )
                                with gr.Tab('Create From Cloud'):
                                    with gr.Column():
                                        cloud_db_create_model = gr.Button(
                                            value="Create Model From Cloud", variant="primary"
                                        )
                                    cloud_db_new_model_name = gr.Textbox(label="Name",
                                                                         placeholder="Model names can only contain alphanumeric and -")
                                    with gr.Row():
                                        cloud_db_create_from_hub = gr.Checkbox(
                                            label="Create From Hub", value=False, visible=False
                                        )
                                        cloud_db_512_model = gr.Checkbox(label="512x Model", value=True)
                                    with gr.Column(visible=False) as hub_row:
                                        cloud_db_new_model_url = gr.Textbox(
                                            label="Model Path",
                                            placeholder="runwayml/stable-diffusion-v1-5",
                                            elem_id="cloud_db_model_path_text_box"
                                        )
                                        cloud_db_new_model_token = gr.Textbox(
                                            label="HuggingFace Token", value=""
                                        )
                                    with gr.Column(visible=True) as local_row:
                                        with gr.Row():
                                            cloud_db_new_model_src = gr.Dropdown(
                                                label="Source Checkpoint",
                                                choices=sorted(get_sd_cloud_models()),
                                                elem_id="cloud_db_source_checkpoint_dropdown"
                                            )
                                            create_refresh_button(
                                                cloud_db_new_model_src,
                                                get_sd_cloud_models,
                                                lambda: {"choices": sorted(get_sd_cloud_models())},
                                                "refresh_sd_models",
                                            )
                                    with gr.Column(visible=False) as shared_row:
                                        with gr.Row():
                                            cloud_db_new_model_shared_src = gr.Dropdown(
                                                label="EXPERIMENTAL: LoRA Shared Diffusers Source",
                                                choices=[],
                                                value=""
                                            )
                                    cloud_db_new_model_extract_ema = gr.Checkbox(
                                        label="Extract EMA Weights", value=False
                                    )
                                    cloud_db_train_unfrozen = gr.Checkbox(label="Unfreeze Model", value=False,
                                                                          elem_id="cloud_db_unfreeze_model_checkbox")
                                    with gr.Row():
                                        gr.HTML(value="<b>Model Creation Jobs Details:<b/>")
                                    with gr.Row():
                                        createmodel_dashboard = gr.Dataframe(
                                            headers=["id", "model name", "status"],
                                            datatype=["str", "str", "str"],
                                            col_count=(3, "fixed"),
                                            value=get_create_model_job_list,
                                            interactive=False,
                                            every=3
                                            # show_progress=True
                                        )

                                def toggle_new_rows(create_from):
                                    return gr.update(visible=create_from), gr.update(visible=not create_from)

                                cloud_db_create_from_hub.change(
                                    fn=toggle_new_rows,
                                    inputs=[cloud_db_create_from_hub],
                                    outputs=[hub_row, local_row],
                                )

                                cloud_db_model_name.change(
                                    _js="clear_loaded",
                                    fn=wrap_load_model_params,
                                    inputs=[cloud_db_model_name],
                                    outputs=[
                                        cloud_db_model_path,
                                        cloud_db_revision,
                                        cloud_db_epochs,
                                        cloud_db_v2,
                                        cloud_db_has_ema,
                                        cloud_db_src,
                                        cloud_db_shared_diffusers_path,
                                        cloud_db_snapshot,
                                        cloud_db_lora_model_name,
                                        cloud_db_status,
                                    ],
                                )
                                cloud_db_create_model.click(
                                    fn=cloud_create_model,
                                    _js="check_create_model_params",
                                    inputs=[
                                        cloud_db_new_model_name,
                                        cloud_db_new_model_src,
                                        cloud_db_new_model_shared_src,
                                        cloud_db_create_from_hub,
                                        cloud_db_new_model_url,
                                        cloud_db_new_model_token,
                                        cloud_db_new_model_extract_ema,
                                        cloud_db_train_unfrozen,
                                        cloud_db_512_model,
                                    ],
                                    outputs=[
                                        createmodel_dashboard
                                        # cloud_db_new_model_name
                                        # cloud_db_create_from_hub
                                        # cloud_db_512_model
                                        # cloud_db_new_model_url
                                        # cloud_db_new_model_token
                                        # cloud_db_new_model_src
                                    ]
                                )
                    break
    return res
