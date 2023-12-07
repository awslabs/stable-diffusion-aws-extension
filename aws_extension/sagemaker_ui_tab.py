import json
import logging
import os

import gradio as gr
import requests

import utils
from aws_extension import sagemaker_ui
from aws_extension.auth_service.simple_cloud_auth import cloud_auth_manager, Admin_Role

from aws_extension.cloud_api_manager.api_manager import api_manager
from aws_extension.sagemaker_ui_utils import create_refresh_button_by_user
from dreambooth_on_cloud.train import get_sorted_cloud_dataset
from modules.ui_common import create_refresh_button
from modules.ui_components import FormRow
import modules.ui
from utils import get_variable_from_json, save_variable_to_json
import datetime

logger = logging.getLogger(__name__)
logger.setLevel(utils.LOGGING_LEVEL)

async_inference_choices = ["ml.g4dn.2xlarge", "ml.g4dn.4xlarge", "ml.g4dn.8xlarge", "ml.g4dn.12xlarge", "ml.g5.2xlarge",
                           "ml.g5.4xlarge", "ml.g5.8xlarge", "ml.g5.12xlarge", "ml.g5.24xlarge"]

test_connection_result = None
api_gateway_url = None
api_key = None
user_table_size = 10

all_resources = [
    'user',
    'sagemaker_endpoint',
    'role',
    'train',
    'checkpoint',
    'inference',
]

all_actions = [
    'all',
    'create',
    'list'
]

all_permissions = []
for resource in all_resources:
    for action in all_actions:
        all_permissions.append(f'{resource}:{action}')


def on_ui_tabs():
    buildin_model_list = ['AWS JumpStart Model', 'AWS BedRock Model', 'Hugging Face Model']
    with gr.Blocks() as sagemaker_interface:
        invisible_user_name_for_ui = gr.Textbox(type='text', visible=False, interactive=False, container=False,
                                                show_label=False, elem_id='invisible_user_name_for_ui')
        with gr.Tab(label='API and User Settings'):
            with gr.Row():
                with gr.Column(variant="panel", scale=1):
                    config_form, disclaimer, whoami_label = api_setting_tab()
                with gr.Column(variant="panel", scale=2, visible=False) as user_setting:
                    with gr.Tab(label='User Management'):
                        _, user_table, user_role_dropdown = user_settings_tab()
                    with gr.Tab(label='Role Management'):
                        _, role_form, role_table = role_settings_tab()
        with gr.Tab(label='Cloud Models Management', variant='panel'):
            with gr.Row():
                # todo: the output message is not right yet
                model_upload, model_list_dataframe = model_upload_tab()
            with gr.Row(visible=False):
                with gr.Row(equal_height=True, elem_id="aws_sagemaker_ui_row", visible=False):
                    sm_load_params = gr.Button(value="Load Settings", elem_id="aws_load_params", visible=False)
                    sm_save_params = gr.Button(value="Save Settings", elem_id="aws_save_params", visible=False)
                    sm_train_model = gr.Button(value="Train", variant="primary", elem_id="aws_train_model",
                                               visible=False)
                    sm_generate_checkpoint = gr.Button(value="Generate Ckpt", elem_id="aws_gen_ckpt", visible=False)

        with gr.Tab(label='Inference Endpoint Management', variant='panel'):
            with gr.Row():
                sagemaker_part = sagemaker_endpoint_tab()
                endpoint_list_df = list_sagemaker_endpoints_tab()
        with gr.Tab(label='Create AWS dataset', variant='panel'):
            with gr.Row():
                dataset_asset = dataset_tab()

        def ui_tab_setup(req: gr.Request):
            logger.debug(f'user {req.username} logged in')
            user = api_manager.get_user_by_username(username=req.username, user_token=req.username)
            admin_visible = False
            sagemaker_create_visible = False
            role_management_visible = False
            if 'roles' in user:
                logger.debug(f"user roles are: {user['roles']}")
                # admin_visible = Admin_Role in user['roles']
                for permission in user['permissions']:
                    if permission == 'user:all' or permission == 'user:create':
                        admin_visible = True
                    if permission == 'sagemaker_endpoint:all' or permission == 'sagemaker_endpoint:create':
                        sagemaker_create_visible = True
                    if permission == 'user:all' or permission == 'role:all' or permission == 'role:create':
                        role_management_visible = True

            # todo: any initial values should from here
            return gr.update(visible=admin_visible or not cloud_auth_manager.api_url), \
                gr.update(visible=admin_visible), \
                gr.update(visible=role_management_visible), \
                gr.update(visible=sagemaker_create_visible), \
                _list_models(req.username, req.username)[0:10], \
                _list_sagemaker_endpoints(req.username), \
                req.username, \
                _list_users(req.username)[:user_table_size], \
                _get_roles_table(req.username)[:10], \
                gr.update(choices=roles(req.username)), \
                f'Welcome, {req.username}'

        sagemaker_interface.load(ui_tab_setup, [], [
            config_form,
            user_setting,
            role_form,
            sagemaker_part,
            model_list_dataframe,
            endpoint_list_df,
            invisible_user_name_for_ui,
            user_table,
            role_table,
            user_role_dropdown,
            whoami_label
        ])

    return (sagemaker_interface, "Amazon SageMaker", "sagemaker_interface"),


def api_setting_tab():
    with gr.Column() as api_setting:
        gr.HTML(value="<u><b>AWS Connection Setting</b></u>")
        gr.HTML(value="Enter your API URL & Token to start the connection.")
        global api_gateway_url
        api_gateway_url = get_variable_from_json('api_gateway_url')
        global api_key
        api_key = get_variable_from_json('api_token')
        with gr.Row() as api_url_form:
            api_url_textbox = gr.Textbox(value=api_gateway_url, lines=1,
                                         placeholder="Please enter API Url of Middle", label="API Url",
                                         elem_id="aws_middleware_api")

            def update_api_gateway_url():
                global api_gateway_url
                api_gateway_url = get_variable_from_json('api_gateway_url')
                return api_gateway_url

            # modules.ui.create_refresh_button(api_url_textbox,
            # get_variable_from_json('api_gateway_url'),
            # lambda: {"value": get_variable_from_json('api_gateway_url')}, "refresh_api_gate_way")
            modules.ui.create_refresh_button(api_url_textbox, update_api_gateway_url,
                                             lambda: {"value": api_gateway_url}, "refresh_api_gateway_url")
        with gr.Row() as api_token_form:
            def update_api_key():
                global api_key
                api_key = get_variable_from_json('api_token')
                return api_key

            api_token_textbox = gr.Textbox(value=api_key, lines=1, placeholder="Please enter API Token",
                                           label="API Token", elem_id="aws_middleware_token")
            modules.ui.create_refresh_button(api_token_textbox, update_api_key, lambda: {"value": api_key},
                                             "refresh_api_token")
        username_textbox, password_textbox, user_settings_form = ui_user_settings_tab()
        with gr.Row():
            global test_connection_result
            test_connection_result = gr.Label(title="Output")
        with gr.Row():
            aws_connect_button = gr.Button(value="Update Setting", variant='primary', elem_id="aws_config_save")
            aws_connect_button.click(_js="update_auth_settings",
                                     fn=update_connect_config,
                                     inputs=[api_url_textbox, api_token_textbox, username_textbox, password_textbox],
                                     outputs=[test_connection_result])
        with gr.Row():
            aws_test_button = gr.Button(value="Test Connection", variant='primary', elem_id="aws_config_test")
            aws_test_button.click(test_aws_connect_config, inputs=[api_url_textbox, api_token_textbox],
                                  outputs=[test_connection_result])

    with gr.Row() as disclaimer_tab:
        with gr.Accordion("Disclaimer", open=False):
            gr.HTML(
                value=
                """You should perform your own independent assessment, and take measures to ensure 
                that you comply with your own specific quality control practices and standards, and the 
                local rules, laws, regulations, licenses and terms of use that apply to you, your content, 
                and the third-party generative AI service in this web UI. Amazon Web Services has no control
                or authority over the third-party generative AI service in this web UI, and does not make
                any representations or warranties that the third-party generative AI service is secure,
                virus-free, operational, or compatible with your production environment and standards.""")

    with gr.Row():
        whoami_label = gr.Label(label='whoami')
    return api_setting, disclaimer_tab, whoami_label


def ui_user_settings_tab():
    with gr.Column() as ui_user_setting:
        gr.HTML('<b>Username</b>')
        with gr.Row():
            username_textbox = gr.Textbox(value=get_variable_from_json('username'), interactive=True,
                                          placeholder='Please enter username', show_label=False)
            modules.ui.create_refresh_button(username_textbox, lambda: get_variable_from_json('username'),
                                             lambda: {"value": get_variable_from_json('username')},
                                             "refresh_username")
        gr.HTML('<b>Password</b>')
        with gr.Row():
            password_textbox = gr.Textbox(type='password', interactive=True,
                                          placeholder='Please enter your password', show_label=False)
            modules.ui.create_refresh_button(password_textbox, lambda: None,
                                             lambda: {"placeholder": 'Please reset your password!'},
                                             "refresh_password")

    return username_textbox, password_textbox, ui_user_setting


def roles(user_token):
    resp = api_manager.list_roles(user_token=user_token)
    return [role['role_name'] for role in resp['roles']]


def user_settings_tab():
    gr.HTML(value="<u><b>Manage User's Access</b></u>")
    with gr.Row(variant='panel') as user_tab:
        with gr.Column(scale=1):

            gr.HTML(value="<b>Update a User Setting</b>")
            username_textbox = gr.Textbox(placeholder="Please enter Enter a username", label="User name")
            pwd_textbox = gr.Textbox(placeholder="Please enter Enter password", label="Password", type='password')
            with gr.Row():
                user_roles_dropdown = gr.Dropdown(multiselect=True, label="User Role")
                create_refresh_button_by_user(user_roles_dropdown,
                                              lambda *args: None,
                                              lambda username: {"choices": roles(username)},
                                              "refresh_create_user_roles")
            upsert_user_button = gr.Button(value="Upsert a User", variant='primary')
            delete_user_button = gr.Button(value="Delete a User", variant='primary')
            user_setting_out_textbox = gr.Textbox(interactive=False, show_label=False)

            def upsert_user(username, password, user_roles, pr: gr.Request):
                try:
                    if not username.rstrip() or len(username.rstrip()) < 1:
                        return f'Please trim trailing spaces. Username should not be none.'
                    if not password or len(password) < 1:
                        return f'Password should not be none.'
                    resp = api_manager.upsert_user(username=username.rstrip(), password=password,
                                                   roles=user_roles, creator=pr.username,
                                                   user_token=pr.username)
                    if resp:
                        return f'User upsert complete "{username}"'
                except Exception as e:
                    return f'User upsert failed: {e}'

            upsert_user_button.click(fn=upsert_user, inputs=[username_textbox, pwd_textbox, user_roles_dropdown],
                                     outputs=[user_setting_out_textbox])

            def delete_user(username):
                try:
                    resp = api_manager.delete_user(username=username, user_token=cloud_auth_manager.username)
                    if resp:
                        return f'User delete complete "{username}"'
                except Exception as e:
                    return f'User delete failed: {e}'

            delete_user_button.click(fn=delete_user, inputs=[username_textbox], outputs=[user_setting_out_textbox])
            # todo: need reload the user table
        with gr.Column(scale=2):
            gr.HTML(value="<b>Users Table</b>")
            user_table = gr.Dataframe(
                headers=["name", "role", "created by"],
                datatype=["str", "str", "str"],
                max_rows=user_table_size,
            )

            def choose_user(evt: gr.SelectData):
                if evt.index[1] != 0:
                    return gr.skip(), gr.skip(), gr.skip()

                # todo: to be done
                user = api_manager.get_user_by_username(evt.value, cloud_auth_manager.username, show_password=True)
                return user['username'], user['password'], user['roles']

            user_table.select(fn=choose_user, inputs=[], outputs=[username_textbox, pwd_textbox, user_roles_dropdown])

            with gr.Row():
                current_page = gr.State(0)
                previous_page_btn = gr.Button(value="Previous Page", variant='primary', visible=False)
                next_page_btn = gr.Button(value="Next Page", variant='primary')

                def list_users_prev(paging, rq: gr.Request):
                    if paging == 0:
                        return gr.skip(), gr.skip()

                    result = _list_users(rq.username)
                    start = paging - user_table_size if paging - user_table_size >= 0 else 0
                    end = start + user_table_size
                    return result[start: end], start

                def list_users_next(paging, rq: gr.Request):
                    result = _list_users(rq.username)
                    if paging >= len(result):
                        return gr.skip(), gr.skip()

                    start = paging + user_table_size if paging + user_table_size < len(result) else paging
                    end = start + user_table_size if start + user_table_size < len(result) else len(result)
                    return result[start: end], start

                next_page_btn.click(fn=list_users_next, inputs=[current_page], outputs=[user_table, current_page])
                previous_page_btn.click(fn=list_users_prev, inputs=[current_page],
                                        outputs=[user_table, current_page])

    return user_tab, user_table, user_roles_dropdown


def role_settings_tab():
    with gr.Column() as ui_role_setting:
        gr.HTML('<u><b>Manage Roles</b></u>')
        with gr.Row(variant='panel') as role_tab:
            with gr.Column(scale=1) as upsert_role_form:
                gr.HTML(value="<b>Update a Role</b>")
                rolename_textbox = gr.Textbox(placeholder="Please enter Enter a role name", label="Role name")
                permissions_dropdown = gr.Dropdown(choices=all_permissions,
                                                   multiselect=True,
                                                   label="Role Permissions")
                upsert_role_button = gr.Button(value="Upsert a Role", variant='primary')
                role_setting_out_textbox = gr.Textbox(interactive=False, show_label=False)

                def upsert_role(role_name, permissions, pr: gr.Request):
                    try:
                        resp = api_manager.upsert_role(role_name=role_name, permissions=permissions,
                                                       creator=pr.username,
                                                       user_token=cloud_auth_manager.username)
                        if resp:
                            return f'Role upsert complete "{role_name}"'
                    except Exception as e:
                        return f'User upsert failed: {e}'

                upsert_role_button.click(fn=upsert_role,
                                         inputs=[rolename_textbox, permissions_dropdown],
                                         outputs=[role_setting_out_textbox]
                                         )

            with gr.Column(scale=2):
                gr.HTML(value="<b>Role Table</b>")
                role_table = gr.Dataframe(
                    headers=["role name", "permissions", "created by"],
                    datatype=["str", "str", "str"],
                    max_rows=10,
                    interactive=False,
                )

                def refresh_roles(pr: gr.Request):
                    return _get_roles_table(pr.username)

                role_table_refresh_button = gr.Button(value='Refresh Role Table', variant='primary')
                role_table_refresh_button.click(fn=refresh_roles, inputs=[], outputs=[role_table])

    return ui_role_setting, upsert_role_form, role_table


def _list_models(username, user_token):
    result = api_manager.list_models_on_cloud(username=username, user_token=user_token, types=None, status=None)
    models = []
    for model in result:
        allowed = ''
        if model['allowed_roles_or_users']:
            allowed = ', '.join(model['allowed_roles_or_users'])
        models.append([model['name'], model['type'], allowed,
                       'In-Use' if model['status'] == 'Active' else 'Disabled', datetime.datetime.fromtimestamp(model['created'])])
    return models


def _get_roles_table(username):
    resp = api_manager.list_roles(user_token=username)
    table = []
    for role in resp['roles']:
        table.append([role['role_name'], ', '.join(role['permissions']), role['creator']])
    return table


def _list_users(username):
    resp = api_manager.list_users(user_token=username)
    if not resp['users']:
        return []

    table = []
    for user in resp['users']:
        table.append([user['username'], ', '.join(user['roles']), user['creator']])

    return table


def model_upload_tab():
    with gr.Column() as upload_tab:
        gr.HTML(value="<b>Upload Model to Cloud</b>")
        # sagemaker_html_log = gr.HTML(elem_id=f'html_log_sagemaker')
        # with gr.Column(variant="panel"):
        with gr.Tab("From WebUI"):
            # gr.HTML(value="<b>Upload Model to S3 from WebUI</b>")
            gr.HTML(value="Refresh to select the model to upload to S3")
            exts = (".bin", ".pt", ".pth", ".safetensors", ".ckpt")
            root_path = os.getcwd()
            model_folders = {
                "ckpt": os.path.join(root_path, "models", "Stable-diffusion"),
                "text": os.path.join(root_path, "embeddings"),
                "lora": os.path.join(root_path, "models", "Lora"),
                "control": os.path.join(root_path, "models", "ControlNet"),
                "hyper": os.path.join(root_path, "models", "hypernetworks"),
                "vae": os.path.join(root_path, "models", "VAE"),
            }

            def scan_local_model_files_by_suffix(suffix):
                model_files = os.listdir(model_folders[suffix])
                # filter non-model files not in exts
                model_files = [f for f in model_files if os.path.splitext(f)[1] in exts]
                model_files = [os.path.join(model_folders[suffix], f) for f in model_files]
                return model_files

            with FormRow(elem_id="model_upload_form_row_01"):
                sd_checkpoints_path = gr.Dropdown(label="SD Checkpoints",
                                                  choices=sorted(scan_local_model_files_by_suffix("ckpt")),
                                                  elem_id="sd_ckpt_dropdown")
                create_refresh_button(sd_checkpoints_path, lambda: None,
                                      lambda: {"choices": sorted(scan_local_model_files_by_suffix("ckpt"))},
                                      "refresh_sd_ckpt")

                textual_inversion_path = gr.Dropdown(label="Textual Inversion",
                                                     choices=sorted(scan_local_model_files_by_suffix("text")),
                                                     elem_id="textual_inversion_model_dropdown")
                create_refresh_button(textual_inversion_path, lambda: None,
                                      lambda: {"choices": sorted(scan_local_model_files_by_suffix("text"))},
                                      "refresh_textual_inversion_model")
            with FormRow(elem_id="model_upload_form_row_02"):
                lora_path = gr.Dropdown(label="LoRA model", choices=sorted(scan_local_model_files_by_suffix("lora")),
                                        elem_id="lora_model_dropdown")
                create_refresh_button(lora_path, lambda: None,
                                      lambda: {"choices": sorted(scan_local_model_files_by_suffix("lora"))},
                                      "refresh_lora_model", )

                controlnet_model_path = gr.Dropdown(label="ControlNet model",
                                                    choices=sorted(scan_local_model_files_by_suffix("control")),
                                                    elem_id="controlnet_model_dropdown")
                create_refresh_button(controlnet_model_path, lambda: None,
                                      lambda: {"choices": sorted(scan_local_model_files_by_suffix("control"))},
                                      "refresh_controlnet_models")
            with FormRow(elem_id="model_upload_form_row_03"):
                hypernetwork_path = gr.Dropdown(label="Hypernetwork",
                                                choices=sorted(scan_local_model_files_by_suffix("hyper")),
                                                elem_id="hyper_model_dropdown")
                create_refresh_button(hypernetwork_path, lambda: None,
                                      lambda: {"choices": sorted(scan_local_model_files_by_suffix("hyper"))},
                                      "refresh_hyper_models")

                vae_path = gr.Dropdown(label="VAE", choices=sorted(scan_local_model_files_by_suffix("vae")),
                                       elem_id="vae_model_dropdown")
                create_refresh_button(vae_path, lambda: None,
                                      lambda: {"choices": sorted(scan_local_model_files_by_suffix("vae"))},
                                      "refresh_vae_models")

            with gr.Column():
                model_update_button = gr.Button(value="Upload Models to Cloud", variant="primary",
                                                elem_id="sagemaker_model_update_button", size=(200, 50))
                webui_upload_model_textbox = gr.Textbox(interactive=False, show_label=False)
                model_update_button.click(fn=sagemaker_ui.sagemaker_upload_model_s3,
                                          # _js="model_update",
                                          inputs=[sd_checkpoints_path, textual_inversion_path, lora_path,
                                                  hypernetwork_path, controlnet_model_path, vae_path],
                                          outputs=[webui_upload_model_textbox, sd_checkpoints_path,
                                                   textual_inversion_path, lora_path, hypernetwork_path,
                                                   controlnet_model_path, vae_path])
        # with gr.Column(variant="panel"):
        with gr.Tab("From My Computer"):
            # gr.HTML(value="<b>Upload Model to S3 from My Computer</b>")
            # gr.HTML(value="Refresh to select the model to upload to S3")
            with FormRow(elem_id="model_upload_local_form_row_01"):
                model_type_drop_down = gr.Dropdown(label="Model Type",
                                                   choices=["SD Checkpoints", "Textual Inversion", "LoRA model",
                                                            "ControlNet model", "Hypernetwork", "VAE"],
                                                   elem_id="model_type_ele_id")
                model_type_hiden_text = gr.Textbox(elem_id="model_type_value_ele_id", visible=False)

                def change_model_type_value(model_type: str):
                    model_type_hiden_text.value = model_type
                    return model_type

                model_type_drop_down.change(fn=change_model_type_value, _js="getModelTypeValue",
                                            inputs=[model_type_drop_down], outputs=model_type_hiden_text)
                file_upload_html_component = gr.HTML(
                    '<input type="file" class="block gradio-html svelte-90oupt padded hide-container" id="file-uploader" multiple onchange="showFileName(event)" style="margin-top: 25px;width:100%">')
            with FormRow(elem_id="model_upload_local_form_row_02"):
                hidden_bind_html = gr.HTML(elem_id="hidden_bind_upload_files",
                                           value="<div id='hidden_bind_upload_files_html'></div>")
            with FormRow(elem_id="model_upload_local_form_row_03"):
                upload_label = gr.HTML(label="upload process", elem_id="progress-bar")
                upload_percent_label = gr.HTML(label="upload percent process", elem_id="progress-percent")
            with gr.Column():
                model_update_button_local = gr.Button(value="Upload Models to Cloud", variant="primary",
                                                      elem_id="sagemaker_model_update_button_local",
                                                      size=(200, 50))
                mycomp_upload_model_textbox = gr.Textbox(interactive=False, show_label=False)
                model_update_button_local.click(_js="uploadFiles",
                                                fn=sagemaker_ui.sagemaker_upload_model_s3_local,
                                                # inputs=[sagemaker_ui.checkpoint_info],
                                                outputs=[mycomp_upload_model_textbox]
                                                )

        with gr.Tab("From URL"):
            with FormRow(elem_id="model_upload_url_form_row_01"):
                model_type_url_drop_down = gr.Dropdown(label="Model Type", choices=["SD Checkpoints", "Textual Inversion", "LoRA model", "ControlNet model", "Hypernetwork", "VAE"], elem_id="model_url_type_ele_id")
            with FormRow(elem_id="model_upload_url_form_row_02"):
                file_upload_url_component = gr.TextArea(label="URL list (Comma-separated in English)", elem_id="model_urls_value_ele_id", placeholder="Best to keep the total model size below 10 GB, and preferably not exceeding 5 urls.")
                file_upload_params_component = gr.TextArea(visible=False, label="Models Description (Optional)", elem_id="model_params_value_ele_id", placeholder='for example:  {"message":"placeholder for chkpts upload test"}')
            with FormRow(elem_id="model_upload_url_form_row_03"):
                file_upload_result_component = gr.Label(elem_id="model_upload_result_value_ele_id")
            with gr.Row():
                model_update_button_local = gr.Button(value="Upload Models to Cloud", variant="primary",
                                                      elem_id="sagemaker_model_update_button_url",
                                                      size=(200, 50))
                model_update_button_local.click(fn=sagemaker_ui.sagemaker_upload_model_s3_url,
                                                inputs=[model_type_url_drop_down, file_upload_url_component,
                                                        file_upload_params_component],
                                                outputs=[file_upload_result_component]
                                                )
    with gr.Column():
        def list_models_prev(paging, rq: gr.Request):
            if paging == 0:
                return gr.skip(), gr.skip()

            result = _list_models(rq.username, rq.username)
            start = paging - 10 if paging - 10 >= 0 else 0
            end = start + 10
            return result[start: end], start

        def list_models_next(paging, rq: gr.Request):
            result = _list_models(rq.username, rq.username)
            if paging >= len(result):
                return gr.skip(), gr.skip()

            start = paging + 10 if paging + 10 < len(result) else paging
            end = start + 10 if start + 10 < len(result) else len(result)
            return result[start: end], start

        current_page = gr.State(0)
        gr.HTML(value="<b>Cloud Model List</b>")
        model_list_df = gr.Dataframe(headers=['name', 'type', 'user/roles', 'status', 'time'],
                                     datatype=['str', 'str', 'str', 'str', 'str']
                                     )
        with gr.Row():
            model_list_prev_btn = gr.Button(value='Previous')
            model_list_next_btn = gr.Button(value='Next')

            model_list_prev_btn.click(fn=list_models_prev, inputs=[current_page], outputs=[model_list_df, current_page])
            model_list_next_btn.click(fn=list_models_next, inputs=[current_page], outputs=[model_list_df, current_page])

    return upload_tab, model_list_df


def sagemaker_endpoint_tab():
    with gr.Column() as sagemaker_tab:
        gr.HTML(value="<b>Deploy New SageMaker Endpoint</b>")

        with gr.Column(variant="panel"):
            default_table = """
                        <table style="width:100%; border: 1px solid black; border-collapse: collapse;">
                          <tr>
                            <th style="border: 1px solid grey; padding: 15px; text-align: left; background-color: #f2f2f2;" colspan="2">Default SageMaker Endpoint Config</th>
                          </tr>
                          <tr>
                            <td style="border: 1px solid grey; padding: 15px; text-align: left;"><b>Instance Type: </b></td>
                            <td style="border: 1px solid grey; padding: 15px; text-align: left;">ml.g5.2xlarge</td>
                          </tr>
                          <tr>
                            <td style="border: 1px solid grey; padding: 15px; text-align: left;"><b>Instance Count</b></td>
                            <td style="border: 1px solid grey; padding: 15px; text-align: left;">1</td>
                          </tr>
                          <tr>
                            <td style="border: 1px solid grey; padding: 15px; text-align: left;"><b>Automatic Scaling</b></td>
                            <td style="border: 1px solid grey; padding: 15px; text-align: left;">yes(range:0-1)</td>
                          </tr>
                        
                        </table>
                    """
            gr.HTML(value=default_table)
            # instance_type_dropdown =
            #   gr.Dropdown(label="SageMaker Instance Type", choices=async_inference_choices, elem_id="sagemaker_inference_instance_type_textbox", value="ml.g4dn.xlarge")
            # instance_count_dropdown =
            #   gr.Dropdown(label="Please select Instance count", choices=["1","2","3","4"], elem_id="sagemaker_inference_instance_count_textbox", value="1")
            endpoint_advance_config_enabled = gr.Checkbox(
                label="Advanced Endpoint Configuration", value=False, visible=True
            )
            with gr.Row(visible=False) as filter_row:
                endpoint_name_textbox = gr.Textbox(value="", lines=1, placeholder="custom endpoint name",
                                                   label="Specify Endpoint Name", visible=True)
                instance_type_dropdown = gr.Dropdown(label="Instance Type", choices=async_inference_choices,
                                                     elem_id="sagemaker_inference_instance_type_textbox",
                                                     value="ml.g5.2xlarge")
                instance_count_dropdown = gr.Dropdown(label="Max Instance count",
                                                      choices=["1", "2", "3", "4", "5", "6"],
                                                      elem_id="sagemaker_inference_instance_count_textbox",
                                                      value="1")
                autoscaling_enabled = gr.Checkbox(
                    label="Enable Autoscaling (0 to Max Instance count)", value=True, visible=True
                )
            with gr.Row():
                user_roles = gr.Dropdown(choices=roles(cloud_auth_manager.username), multiselect=True,
                                         label="User Role")
                create_refresh_button_by_user(
                    user_roles,
                    lambda *args: None,
                    lambda username: {
                        'choices': roles(username)
                    },
                    'refresh_sagemaker_user_roles'
                )
            sagemaker_deploy_button = gr.Button(value="Deploy", variant='primary',
                                                elem_id="sagemaker_deploy_endpoint_button")
            create_ep_output_textbox = gr.Textbox(interactive=False, show_label=False)

            def _create_sagemaker_endpoint(endpoint_name, instance_type, scale_count, autoscale, target_user_roles, pr: gr.Request):
                return api_manager.sagemaker_deploy(endpoint_name=endpoint_name,
                                                    instance_type=instance_type,
                                                    initial_instance_count=scale_count,
                                                    autoscaling_enabled=autoscale,
                                                    user_roles=target_user_roles,
                                                    user_token=pr.username
                                                    )

            sagemaker_deploy_button.click(fn=_create_sagemaker_endpoint,
                                          inputs=[endpoint_name_textbox, instance_type_dropdown,
                                                  instance_count_dropdown, autoscaling_enabled, user_roles],
                                          outputs=[create_ep_output_textbox])  # todo: make a new output


        def toggle_new_rows(checkbox_state):
            if checkbox_state:
                return gr.update(visible=True)
            else:
                return gr.update(visible=False)

        endpoint_advance_config_enabled.change(
            fn=toggle_new_rows,
            inputs=endpoint_advance_config_enabled,
            outputs=filter_row
        )

        with gr.Column(title="Delete SageMaker Endpoint", variant='panel'):
            gr.HTML(value="<u><b>Delete SageMaker Endpoint</b></u>")
            with gr.Row():
                # todo: this list is not safe
                sagemaker_endpoint_delete_dropdown = gr.Dropdown(choices=api_manager.list_all_sagemaker_endpoints(username=cloud_auth_manager.username, user_token=cloud_auth_manager.username),
                                                                 multiselect=True,
                                                                 label="Select Cloud SageMaker Endpoint")
                modules.ui.create_refresh_button(sagemaker_endpoint_delete_dropdown,
                                                 lambda: None,
                                                 lambda: {"choices": api_manager.list_all_sagemaker_endpoints(username=cloud_auth_manager.username, user_token=cloud_auth_manager.username)},
                                                 "refresh_sagemaker_endpoints_delete")

            sagemaker_endpoint_delete_button = gr.Button(value="Delete", variant='primary',
                                                         elem_id="sagemaker_endpoint_delete_button")
            delete_ep_output_textbox = gr.Textbox(interactive=False, show_label=False)

            def _endpoint_delete(endpoints, pr: gr.Request):
                return api_manager.sagemaker_endpoint_delete(delete_endpoint_list=endpoints, user_token=pr.username)

            sagemaker_endpoint_delete_button.click(_endpoint_delete,
                                                   inputs=[sagemaker_endpoint_delete_dropdown],
                                                   outputs=[delete_ep_output_textbox])

        return sagemaker_tab


def _list_sagemaker_endpoints(username):
    resp = api_manager.list_all_sagemaker_endpoints_raw(username=username, user_token=username)
    endpoints = []
    for endpoint in resp:
        if 'owner_group_or_role' in endpoint and endpoint['owner_group_or_role']:
            endpoint_roles = ','.join(endpoint['owner_group_or_role'])
            endpoints.append([
                endpoint['EndpointDeploymentJobId'][:4],
                endpoint['endpoint_name'],
                endpoint_roles,
                endpoint['autoscaling'],
                endpoint['endpoint_status'],
                endpoint['current_instance_count'] if endpoint['current_instance_count'] else "0",
                endpoint['startTime'].split(' ')[0] if endpoint['startTime'] else "",
            ])
    return endpoints


def list_sagemaker_endpoints_tab():
    with gr.Column():
        gr.HTML(value="<b>Sagemaker Endpoints List</b>")
        model_list_df = gr.Dataframe(
            headers=['id', 'name', 'owners', 'autoscaling', 'status', 'instance', 'created time'],
            datatype=['str', 'str', 'str', 'str', 'str', 'str', 'str']
            )

        def list_ep_prev(paging, rq: gr.Request):
            if paging == 0:
                return gr.skip(), gr.skip()

            result = _list_sagemaker_endpoints(rq.username)
            start = paging - 10 if paging - 10 >= 0 else 0
            end = start + 10
            return result[start: end], start

        def list_ep_next(paging, rq: gr.Request):
            result = _list_sagemaker_endpoints(rq.username)
            if paging >= len(result):
                return gr.skip(), gr.skip()

            start = paging + 10 if paging + 10 < len(result) else paging
            end = start + 10 if start + 10 < len(result) else len(result)
            return result[start: end], start

        current_page = gr.State(0)

        with gr.Row():
            ep_list_prev_btn = gr.Button(value='Previous')
            ep_list_next_btn = gr.Button(value='Next')

        ep_list_next_btn.click(fn=list_ep_next, inputs=[current_page], outputs=[model_list_df, current_page])
        ep_list_prev_btn.click(fn=list_ep_prev, inputs=[current_page], outputs=[model_list_df, current_page])
        return model_list_df


def dataset_tab():
    with gr.Row() as dt:
        with gr.Column(variant='panel'):
            gr.HTML(value="<u><b>Create a Dataset</b></u>")

            def upload_file(files):
                file_paths = [file.name for file in files]
                return file_paths

            file_output = gr.File()
            upload_button = gr.UploadButton("Click to Upload a File", file_types=["image", "video"],
                                            file_count="multiple")
            upload_button.upload(fn=upload_file, inputs=[upload_button], outputs=[file_output])

            def create_dataset(files, dataset_name, dataset_desc, pr: gr.Request):
                logger.debug(dataset_name)
                dataset_content = []
                file_path_lookup = {}
                for file in files:
                    orig_name = file.name.split(os.sep)[-1]
                    file_path_lookup[orig_name] = file.name
                    dataset_content.append(
                        {
                            "filename": orig_name,
                            "name": orig_name,
                            "type": "image",
                            "params": {}
                        }
                    )

                payload = {
                    "dataset_name": dataset_name,
                    "content": dataset_content,
                    "params": {
                        "description": dataset_desc
                    },
                    "creator": pr.username
                }

                url = get_variable_from_json('api_gateway_url') + '/dataset'
                api_key = get_variable_from_json('api_token')

                raw_response = requests.post(url=url, json=payload, headers={'x-api-key': api_key})
                raw_response.raise_for_status()
                response = raw_response.json()

                logger.info(f"Start upload sample files response:\n{response}")
                for filename, presign_url in response['s3PresignUrl'].items():
                    file_path = file_path_lookup[filename]
                    with open(file_path, 'rb') as f:
                        response = requests.put(presign_url, f)
                        logger.info(response)
                        response.raise_for_status()

                payload = {
                    "dataset_name": dataset_name,
                    "status": "Enabled"
                }

                raw_response = requests.put(url=url, json=payload, headers={'x-api-key': api_key})
                raw_response.raise_for_status()
                logger.debug(raw_response.json())
                return f'Complete Dataset {dataset_name} creation', None, None, None, None

            dataset_name_upload = gr.Textbox(value="", lines=1, placeholder="Please input dataset name",
                                             label="Dataset Name", elem_id="sd_dataset_name_textbox")
            dataset_description_upload = gr.Textbox(value="", lines=1,
                                                    placeholder="Please input dataset description",
                                                    label="Dataset Description",
                                                    elem_id="sd_dataset_description_textbox")
            create_dataset_button = gr.Button("Create Dataset", variant="primary",
                                              elem_id="sagemaker_dataset_create_button")  # size=(200, 50)
            dataset_create_result = gr.Textbox(value="", label="Create Result", interactive=False)
            create_dataset_button.click(
                fn=create_dataset,
                inputs=[upload_button, dataset_name_upload, dataset_description_upload],
                outputs=[
                    dataset_create_result,
                    dataset_name_upload,
                    dataset_description_upload,
                    file_output,
                    upload_button
                ],
                show_progress=True
            )

        with gr.Column(variant='panel'):
            gr.HTML(value="<u><b>Browse a Dataset</b></u>")

            with gr.Row():
                cloud_dataset_name = gr.Dropdown(
                    label="Dataset From Cloud",
                    elem_id="cloud_dataset_dropdown",
                    info="choose datasets from cloud"
                )

                create_refresh_button_by_user(
                    cloud_dataset_name,
                    lambda *args: None,
                    lambda username: {
                        'choices': [ds['datasetName'] for ds in get_sorted_cloud_dataset(username)]
                    },
                    "refresh_cloud_dataset",
                )
            with gr.Row():
                dataset_s3_output = gr.Textbox(label='dataset s3 location', show_label=True,
                                               type='text').style(show_copy_button=True)
            with gr.Row():
                dataset_des_output = gr.Textbox(label='dataset description', show_label=True, type='text')
            with gr.Row():
                dataset_gallery = gr.Gallery(
                    label="Dataset images", show_label=False, elem_id="gallery",
                ).style(columns=[2], rows=[2], object_fit="contain", height="auto")

                def get_results_from_datasets(dataset_name, pr: gr.Request):
                    resp = api_manager.get_dataset_items_from_dataset(dataset_name, pr.username)
                    dataset_items = [(item['preview_url'], item['key']) for item in
                                     resp['data']]
                    return resp['s3'], resp['description'], dataset_items

                cloud_dataset_name.select(fn=get_results_from_datasets, inputs=[cloud_dataset_name],
                                          outputs=[dataset_s3_output, dataset_des_output, dataset_gallery])

    return dt


def update_connect_config(api_url, api_token, username=None, password=None, initial=True):
    # Check if api_url ends with '/', if not append it
    if not api_url.endswith('/'):
        api_url += '/'

    save_variable_to_json('api_gateway_url', api_url)
    save_variable_to_json('api_token', api_token)
    save_variable_to_json('username', username)
    global api_gateway_url
    api_gateway_url = get_variable_from_json('api_gateway_url')
    global api_key
    api_key = get_variable_from_json('api_token')
    sagemaker_ui.init_refresh_resource_list_from_cloud(username)
    try:
        if not api_manager.upsert_user(username=username, password=password, roles=[], creator=username,
                                       initial=initial, user_token=username):
            return 'Initial Setup Failed'
    except Exception as e:
        return f'User upsert failed: {e}'
    return "Setting updated"


def test_aws_connect_config(api_url, api_token):
    # update_connect_config(api_url, api_token, initial=False)
    api_url = get_variable_from_json('api_gateway_url')
    api_token = get_variable_from_json('api_token')
    if not api_url.endswith('/'):
        api_url += '/'
    target_url = f'{api_url}inference/test-connection'
    headers = {
        "x-api-key": api_token,
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(target_url,
                                headers=headers)  # Assuming sagemaker_ui.server_request is a wrapper around requests
        response.raise_for_status()  # Raise an exception if the HTTP request resulted in an error
        r = response.json()
        return "Successfully Connected"
    except requests.exceptions.RequestException as e:
        logger.error(f"Error: Failed to get server request. Details: {e}")
        return "failed to connect to backend server, please check the url and token"
