import datetime
import json
import logging
import os
import subprocess
import threading

import gradio as gr
import modules.ui
import requests
from modules import shared
from modules.ui_common import create_refresh_button
from modules.ui_components import FormRow
from modules.ui_components import ToolButton

import utils
from aws_extension import sagemaker_ui
from aws_extension.auth_service.simple_cloud_auth import cloud_auth_manager
from aws_extension.cloud_api_manager.api import api, client_api_version
from aws_extension.cloud_api_manager.api_manager import api_manager
from aws_extension.cloud_dataset_manager.dataset_manager import get_sorted_cloud_dataset
from aws_extension.sagemaker_ui import checkpoint_type
from aws_extension.sagemaker_ui_utils import create_refresh_button_by_user
from utils import get_variable_from_json, save_variable_to_json, has_config, is_gcr

logger = logging.getLogger(__name__)
logger.setLevel(utils.LOGGING_LEVEL)

endpoint_type_choices = ["Async", "Real-time"]

if is_gcr():
    inference_choices = ["ml.g4dn.2xlarge",
                         "ml.g4dn.4xlarge",
                         "ml.g4dn.8xlarge",
                         "ml.g4dn.12xlarge"
                         ]
    inference_choices_default = "ml.g4dn.2xlarge"
else:
    inference_choices = ["ml.g4dn.2xlarge",
                         "ml.g4dn.4xlarge",
                         "ml.g4dn.8xlarge",
                         "ml.g4dn.12xlarge",
                         "ml.g5.2xlarge",
                         "ml.g5.4xlarge",
                         "ml.g5.8xlarge",
                         "ml.g5.12xlarge",
                         "ml.g5.24xlarge",
                         "ml.p4d.24xlarge",
                         ]
    inference_choices_default = "ml.g5.2xlarge"

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
    # 'create',
    # 'list'
    # 'delete'
]

all_permissions = []
for resource in all_resources:
    for action in all_actions:
        all_permissions.append(f'{resource}:{action}')


def run_command():
    subprocess.run(["sleep", "5"])
    subprocess.run(["sudo", "systemctl", "restart", "sd-webui.service"])


def restart_sd_webui_service():
    thread = threading.Thread(target=run_command)
    thread.start()
    return "Restarting the service after 5 seconds..."


def on_ui_tabs():
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
                    with gr.Row():
                        version_label = gr.Label(
                            label='Version',
                            value=f'Client Version: {client_api_version}',
                        )
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
                sagemaker_part = ep_create_tab()
                endpoint_list_df = ep_list_tab()
        with gr.Tab(label='Datasets Management', variant='panel'):
            with gr.Row():
                dataset_tab()
        with gr.Tab(label='Train Management', variant='panel'):
            with gr.Row():
                train_list = trainings_tab()

        def get_version_info():
            if not hasattr(shared.demo.server_app, 'api_version'):
                return f'Front-end Version: {client_api_version}'

            if shared.demo.server_app.api_version == client_api_version:
                return f'Front-end & Middleware API Version: {client_api_version}'

            version = f'Front-end Version {client_api_version}'

            if shared.demo.server_app.api_version:

                if client_api_version > shared.demo.server_app.api_version:
                    version += (f' > Middleware API Version {shared.demo.server_app.api_version},'
                                f' please update the Middleware API')

                if client_api_version < shared.demo.server_app.api_version:
                    version += (f' < Middleware API Version {shared.demo.server_app.api_version},'
                                f' please update the Front-end')

            return version

        def ui_tab_setup(req: gr.Request):
            logger.debug(f'user {req.username} logged in')
            user = api_manager.get_user_by_username(username=req.username, h_username=req.username)
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
                _list_models(req.username)[0:10], \
                _list_trainings_job(req.username), \
                _list_sagemaker_endpoints(req.username), \
                req.username, \
                _list_users(req.username, None, None)[:user_table_size], \
                _get_roles_table(req.username)[:10], \
                gr.update(choices=roles(req.username)), \
                f'Welcome, {req.username}!', \
                get_version_info()

        sagemaker_interface.load(ui_tab_setup, [], [
            config_form,
            user_setting,
            role_form,
            sagemaker_part,
            model_list_dataframe,
            train_list,
            endpoint_list_df,
            invisible_user_name_for_ui,
            user_table,
            role_table,
            user_role_dropdown,
            whoami_label,
            version_label
        ])

    return (sagemaker_interface, "Amazon SageMaker", "sagemaker_interface"),


def api_setting_tab():
    with gr.Column() as api_setting:
        gr.HTML(value="<u><b>AWS Connection Setting</b></u>")
        gr.HTML(value="Enter your API URL & Token to start the connection.")

        with gr.Row():
            api_url_textbox = gr.Textbox(value=utils.host_url(),
                                         lines=1,
                                         placeholder="Please enter API URL",
                                         label="API URL (ApiGatewayUrl)",
                                         interactive=True,
                                         elem_id="aws_api_url")
            modules.ui.create_refresh_button(api_url_textbox, lambda: utils.host_url(),
                                             lambda: {"value": utils.host_url()},
                                             "refresh_url_btn")
        with gr.Row():
            api_token_textbox = gr.Textbox(value=utils.api_key(),
                                           lines=1,
                                           placeholder="Please enter API Token",
                                           label="API Token (ApiGatewayUrlToken)",
                                           interactive=True,
                                           elem_id="aws_api_gateway_url_token")
            modules.ui.create_refresh_button(api_token_textbox, lambda: utils.api_key(),
                                             lambda: {"value": utils.api_key()},
                                             "refresh_api_token")
        with gr.Row():
            username_textbox = gr.Textbox(value=utils.username(),
                                          interactive=True,
                                          placeholder='Please enter username',
                                          label="Username")
            modules.ui.create_refresh_button(username_textbox, lambda: utils.username(),
                                             lambda: {"value": utils.username()},
                                             "refresh_username")
        with gr.Row():
            password_textbox = gr.Textbox(type='password',
                                          interactive=True,
                                          placeholder='Please enter your password',
                                          label="Password")
            modules.ui.create_refresh_button(password_textbox, lambda: None,
                                             lambda: {"placeholder": 'Please reset your password!'},
                                             "refresh_password")
        with gr.Row():
            connection_output = gr.Label(title="Output", visible=True, show_label=False)
        with gr.Row():
            aws_connect_button = gr.Button(value="Test Connection & Update Setting",
                                           variant='primary',
                                           elem_id="aws_config_save")
        with gr.Row():
            restart_service = gr.Button(value="Restart WebUI",
                                        elem_id="restart_service")

            def update_connect_config(api_url, api_token, username=None, password=None, initial=True):
                show_output = connection_output.update(visible=True)
                if api_url == 'cancelled':
                    return show_output, "cancelled"

                if not api_url:
                    return show_output, "Please input api url"

                if not api_token:
                    return show_output, "Please input api token"

                # Check if api_url ends with '/', if not append it
                if not api_url.endswith('/'):
                    api_url += '/'

                if not test_aws_connect_config(api_url, api_token):
                    return show_output, "Failed to connect to backend server, please check your API version or url and token"

                message = "Successfully Connected"
                save_variable_to_json('api_gateway_url', api_url)
                save_variable_to_json('api_token', api_token)
                save_variable_to_json('username', username)
                sagemaker_ui.init_refresh_resource_list_from_cloud(username)
                try:
                    if not api_manager.upsert_user(username=username,
                                                   password=password,
                                                   roles=[],
                                                   creator=username,
                                                   initial=initial):
                        return show_output, f'{message}, but update setting failed'
                except Exception as e:
                    return show_output, f'{message}, but update setting failed, because {e}'

                if os.path.exists("/etc/systemd/system/sd-webui.service"):
                    restart_sd_webui_service()
                    return show_output, f"Setting Updated, Service will restart in 5 seconds"

                return show_output, f"{message} & Setting Updated"

            aws_connect_button.click(_js="update_auth_settings",
                                     fn=update_connect_config,
                                     inputs=[api_url_textbox, api_token_textbox, username_textbox, password_textbox],
                                     outputs=[connection_output, connection_output])

            restart_service.click(fn=restart_sd_webui_service, inputs=[], outputs=[connection_output])

    with gr.Row(visible=has_config()) as disclaimer_tab:
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

    with gr.Row(visible=has_config()):
        whoami_label = gr.Label(label='Current User')

    with gr.Row(visible=has_config()):
        logout_btn = gr.Button(value='Logout')
        logout_btn.click(fn=lambda: None, _js="logout", inputs=[], outputs=[])

    return api_setting, disclaimer_tab, whoami_label


def roles(username):
    resp = api_manager.list_roles(username=username)
    return [role['role_name'] for role in resp['roles']]


def user_settings_tab():
    gr.HTML(value="<u><b>Manage User's Access</b></u>")
    with gr.Row(variant='panel') as user_tab:
        with gr.Column(scale=1):

            gr.HTML(value="<b>Update a User Setting</b>")
            username_textbox = gr.Textbox(placeholder="Please Enter a username", label="User name")
            pwd_textbox = gr.Textbox(placeholder="Please Enter password", label="Password", type='password')
            with gr.Row():
                user_roles_dropdown = gr.Dropdown(multiselect=True, label="User Role")
                create_refresh_button_by_user(user_roles_dropdown,
                                              lambda *args: None,
                                              lambda username: {"choices": roles(username)},
                                              "refresh_create_user_roles")
            upsert_user_button = gr.Button(value="Insert or Update a User", variant='primary')
            delete_user_button = gr.Button(value="Delete a User", variant='primary')
            user_setting_output = gr.Textbox(interactive=False, show_label=False, visible=True)

            def upsert_user(username, password, user_roles, pr: gr.Request):
                show_output = user_setting_output.update(visible=True)
                try:
                    if not username.rstrip() or len(username.rstrip()) < 1:
                        return f'Please trim trailing spaces. Username should not be none.', show_output
                    if not password or len(password) < 1:
                        return f'Password should not be none.', show_output

                    resp = api_manager.upsert_user(username=username.rstrip(), password=password,
                                                   roles=user_roles, creator=pr.username)
                    if resp:
                        return f'User upsert complete "{username}"', show_output
                except Exception as e:
                    return f'User upsert failed: {e}', show_output

            upsert_user_button.click(fn=upsert_user, inputs=[username_textbox, pwd_textbox, user_roles_dropdown],
                                     outputs=[user_setting_output, user_setting_output])

            def delete_user(username):
                if not username or len(username) < 1:
                    return f'Username should not be none.'

                try:
                    resp = api_manager.delete_user(username=username, user_token=cloud_auth_manager.username)
                    if resp:
                        return f'User delete complete "{username}"'
                except Exception as e:
                    return f'User delete failed: {e}'

            delete_user_button.click(fn=delete_user, inputs=[username_textbox], outputs=[user_setting_output])
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
                user = api_manager.get_user_by_username(username=evt.value, h_username=cloud_auth_manager.username,
                                                        show_password=True)
                return user['username'], user['password'], user['roles']

            def search_users(name: str, role: str, paging, rq: gr.Request):
                result = _list_users(rq.username, name, role)
                if len(result) == 0:
                    return None, gr.skip()
                if paging >= len(result):
                    return gr.skip(), gr.skip()
                start = paging + user_table_size if paging + user_table_size < len(result) else paging
                end = start + user_table_size if start + user_table_size < len(result) else len(result)
                return result[start: end], start

            user_table.select(fn=choose_user, inputs=[], outputs=[username_textbox, pwd_textbox, user_roles_dropdown])
            with gr.Accordion("Users Table Filter", open=False):
                with gr.Row():
                    name_search_textbox = gr.Textbox(ele_id="name_search_txt", label="Search by Name",
                                                     placeholder="role name")
                    role_search_dropdown = gr.Dropdown(ele_id="role_search_drop", label="Search by Role",
                                                       choices=[''] + roles(cloud_auth_manager.username))

            with gr.Row():
                current_page = gr.State(0)
                previous_page_btn = gr.Button(value="Previous Page", variant='primary')
                next_page_btn = gr.Button(value="Next Page", variant='primary')

                def list_users_prev(name, role, paging, rq: gr.Request):
                    if paging == 0:
                        return gr.skip(), gr.skip()

                    result = _list_users(rq.username, name, role)
                    start = paging - user_table_size if paging - user_table_size >= 0 else 0
                    end = start + user_table_size
                    return result[start: end], start

                def list_users_next(name, role, paging, rq: gr.Request):
                    result = _list_users(rq.username, name, role)
                    if paging >= len(result):
                        return gr.skip(), gr.skip()

                    start = paging + user_table_size if paging + user_table_size < len(result) else paging
                    end = start + user_table_size if start + user_table_size < len(result) else len(result)
                    return result[start: end], start

                next_page_btn.click(fn=list_users_next,
                                    inputs=[name_search_textbox, role_search_dropdown, current_page],
                                    outputs=[user_table, current_page])
                previous_page_btn.click(fn=list_users_prev,
                                        inputs=[name_search_textbox, role_search_dropdown, current_page],
                                        outputs=[user_table, current_page])
            name_search_textbox.submit(fn=search_users,
                                       inputs=[name_search_textbox, role_search_dropdown, current_page],
                                       outputs=[user_table, current_page])
            role_search_dropdown.change(fn=search_users,
                                        inputs=[name_search_textbox, role_search_dropdown, current_page],
                                        outputs=[user_table, current_page])

    return user_tab, user_table, user_roles_dropdown


def role_settings_tab():
    with gr.Column() as ui_role_setting:
        gr.HTML('<u><b>Manage Roles</b></u>')
        with gr.Row(variant='panel') as role_tab:
            with gr.Column(scale=1) as upsert_role_form:
                gr.HTML(value="<b>Update a Role</b>")
                role_name_textbox = gr.Textbox(placeholder="Please Enter a role name", label="Role name")
                permissions_dropdown = gr.Dropdown(choices=all_permissions,
                                                   multiselect=True,
                                                   label="Role Permissions")
                upsert_role_button = gr.Button(value="Insert or Update a Role", variant='primary')
                role_setting_output = gr.Textbox(interactive=False, show_label=False, visible=True)

                def upsert_role(role_name, permissions, pr: gr.Request):
                    show_output = role_setting_output.update(visible=True)
                    if not role_name or not permissions:
                        return 'Please input role name and permissions.', show_output

                    try:
                        resp = api_manager.upsert_role(role_name=role_name, permissions=permissions,
                                                       creator=pr.username)
                        if resp:
                            return f'Role upsert complete "{role_name}"', show_output
                    except Exception as e:
                        return f'Role upsert failed: {e}', show_output

                upsert_role_button.click(fn=upsert_role,
                                         inputs=[role_name_textbox, permissions_dropdown],
                                         outputs=[role_setting_output, role_setting_output]
                                         )

            with gr.Column(scale=2):
                gr.HTML(value="<b>Role Table</b>")
                role_table = gr.Dataframe(
                    headers=["role name", "permissions", "created by"],
                    datatype=["str", "str", "str"],
                    max_rows=user_table_size,
                    interactive=False,
                )

                with gr.Row():
                    current_page = gr.State(0)
                    previous_page_btn = gr.Button(value="Previous Page", variant='primary')
                    next_page_btn = gr.Button(value="Next Page", variant='primary')

                    def list_roles_prev(paging, rq: gr.Request):
                        if paging == 0:
                            return gr.skip(), gr.skip()

                        result = _get_roles_table(rq.username)
                        start = paging - user_table_size if paging - user_table_size >= 0 else 0
                        end = start + user_table_size
                        return result[start: end], start

                    def list_roles_next(paging, rq: gr.Request):
                        result = _get_roles_table(rq.username)

                        if paging >= len(result):
                            return gr.skip(), gr.skip()

                        start = paging + user_table_size if paging + user_table_size < len(result) else paging
                        end = start + user_table_size if start + user_table_size < len(result) else len(result)
                        return result[start: end], start

                    next_page_btn.click(fn=list_roles_next, inputs=[current_page], outputs=[role_table, current_page])
                    previous_page_btn.click(fn=list_roles_prev, inputs=[current_page],
                                            outputs=[role_table, current_page])

    return ui_role_setting, upsert_role_form, role_table


def _list_models(username):
    result = api_manager.list_models_on_cloud(username=username, types=None, status=None)
    models = []
    for model in result:
        allowed = ''
        if model['allowed_roles_or_users']:
            allowed = ', '.join(model['allowed_roles_or_users'])
        models.append([
            model['name'],
            model['type'],
            allowed,
            model['status'],
            datetime.datetime.fromtimestamp(model['created']),
            model['id'],
        ],
        ),

    if len(models) == 0:
        return [['', '', '', '', '', '']]

    return models


def _get_roles_table(username):
    resp = api_manager.list_roles(username=username)
    table = []
    for role in resp['roles']:
        table.append([role['role_name'], ', '.join(role['permissions']), role['creator']])
    return table


def _list_users(username, name, role):
    resp = api_manager.list_users(username=username)
    if not resp['users']:
        return []

    table = []
    for user in resp['users']:
        if name and name not in user['username']:
            continue
        if role and role not in user['roles']:
            continue
        table.append([user['username'], ', '.join(user['roles']), user['creator']])

    return table


def model_upload_tab():
    with gr.Column(scale=1) as upload_tab:
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
                                                elem_id="sagemaker_model_update_button")
                webui_upload_model_textbox = gr.Textbox(interactive=False, show_label=False)
                model_update_button.click(fn=sagemaker_ui.sagemaker_upload_model_s3,
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
                                                      elem_id="sagemaker_model_update_button_local")
                mycomp_upload_model_textbox = gr.Textbox(interactive=False, show_label=False)
                model_update_button_local.click(_js="uploadFiles",
                                                fn=sagemaker_ui.sagemaker_upload_model_s3_local,
                                                outputs=[mycomp_upload_model_textbox]
                                                )

        with gr.Tab("From URL"):
            with FormRow(elem_id="model_upload_url_form_row_01"):
                model_type_url_drop_down = gr.Dropdown(label="Model Type",
                                                       choices=["SD Checkpoints", "Textual Inversion", "LoRA model",
                                                                "ControlNet model", "Hypernetwork", "VAE"],
                                                       elem_id="model_url_type_ele_id")
            with FormRow(elem_id="model_upload_url_form_row_02"):
                file_upload_url_component = gr.TextArea(label="URL List (Comma-separated in English)",
                                                        elem_id="model_urls_value_ele_id",
                                                        placeholder="Best to keep the total model size below 10 GB, and preferably not exceeding 5 urls.")
                file_upload_params_component = gr.TextArea(label="Models Description (Optional)",
                                                           elem_id="model_params_value_ele_id",
                                                           placeholder='for example: placeholder for chkpts upload test')
            with FormRow(elem_id="model_upload_url_form_row_03"):
                file_upload_result_component = gr.Label(elem_id="model_upload_result_value_ele_id")
            with gr.Row():
                model_update_button_local = gr.Button(value="Upload Models to Cloud", variant="primary",
                                                      elem_id="sagemaker_model_update_button_url")
                model_update_button_local.click(fn=sagemaker_ui.sagemaker_upload_model_s3_url,
                                                inputs=[model_type_url_drop_down, file_upload_url_component,
                                                        file_upload_params_component],
                                                outputs=[file_upload_result_component]
                                                )

    with gr.Column(scale=2):

        def list_ckpts_data(query_types, query_status, query_roles, current_page, rq: gr.Request):
            default_list = [['', '', '', '', '', '']]
            show_page_info = page_info.update(visible=True)

            params = {
                'types': query_types,
                'status': query_status,
                'roles': query_roles,
                'page': int(current_page),
                'username': rq.username,
            }
            api.set_username(rq.username)

            if not has_config():
                return default_list, show_page_info, 'Please config api url and token first'

            resp = api.list_checkpoints(params=params)
            models = []

            if 'data' not in resp.json():
                logger.error(f"list_checkpoints: {resp.json()}")
                return default_list, show_page_info, 'No data'

            page = resp.json()['data']['page']
            per_page = resp.json()['data']['per_page']
            total = resp.json()['data']['total']
            pages = resp.json()['data']['pages']

            if len(resp.json()['data']['checkpoints']) == 0:
                return default_list, show_page_info, 'No data'

            for model in resp.json()['data']['checkpoints']:
                allowed = ''
                if model['allowed_roles_or_users']:
                    allowed = ', '.join(model['allowed_roles_or_users'])
                models.append([
                    model['name'],
                    model['type'],
                    allowed,
                    model['status'],
                    datetime.datetime.fromtimestamp(float(model['created'])),
                    model['id'],
                ])

            return models, show_page_info, f"Page: {page}/{pages}    Total: {total} items    PerPage: {per_page}"

        gr.HTML(value="<b>Cloud Model List</b>")
        model_list = gr.Dataframe(headers=['name', 'type', 'user/roles', 'status', 'time', 'id'],
                                  datatype=['str', 'str', 'str', 'str', 'str', 'str'],
                                  interactive=False,
                                  )
        page_info = gr.Textbox(label="Page Info", interactive=False, show_label=False, visible=False)
        with gr.Row():
            with gr.Column():
                current_page = gr.Number(label="Page Number", value=1, minimum=1, step=1)
            with gr.Column():
                query_types = gr.Dropdown(
                    multiselect=True,
                    choices=checkpoint_type,
                    label="Types")
            with gr.Column():
                query_status = gr.Dropdown(
                    multiselect=True,
                    choices=['Active', 'Initial'],
                    label="Status")
            with gr.Column():
                query_roles = gr.Dropdown(
                    multiselect=True,
                    choices=roles(cloud_auth_manager.username),
                    label="Roles")
        with gr.Row():
            refresh_button = gr.Button(value="Refresh List",  variant="primary", elem_id="refresh_ckpts_button_id")
            refresh_button.click(
                fn=list_ckpts_data,
                inputs=[query_types, query_status, query_roles, current_page],
                outputs=[model_list, page_info, page_info]
            )
        with gr.Row():
            gr.HTML(value="<b>Cloud Model Delete or Rename</b>")
        with gr.Row():
            ckpt_list_info = gr.Textbox(show_label=False,
                                        interactive=False,
                                        value="Please select one checkpoint to delete or rename",)
            ckpt_list_selected = gr.Textbox(show_label=False, interactive=False, visible=False)
        with gr.Row():

            new_name_textbox = gr.TextArea(placeholder="Input new Checkpoint name",
                                           show_label=False,
                                           lines=1,
                                           elem_id="new_ckpt_value_ele_id")

            ckpts_rename_button = gr.Button(value='Rename Checkpoint', elem_id="ckpts_rename_btn")

            # ---- bind functions start ----
            def choose_model(evt: gr.SelectData, models):
                row_index = evt.index[0]
                model_name = models.values[row_index][5]
                if model_name:
                    message = f"You selected model is: {model_name}"
                else:
                    message = "No model selected"
                    model_name = ""
                return message, model_name
            model_list.select(fn=choose_model, inputs=[model_list], outputs=[ckpt_list_info, ckpt_list_selected])

            def _rename_ckpt(ckpt_id, new_name, pr: gr.Request):
                show_output = ckpt_list_info.update(visible=True)
                if not ckpt_id:
                    return 'Please select one checkpoint to rename.', show_output, ''
                if not new_name:
                    return 'Please input new name.', show_output, ''
                return api_manager.ckpt_rename(ckpt_id=ckpt_id, name=new_name, user_token=pr.username), show_output, ''

            ckpts_rename_button.click(_rename_ckpt,
                                      inputs=[ckpt_list_selected, new_name_textbox],
                                      outputs=[ckpt_list_info, ckpt_list_info, ckpt_list_selected])

            def _delete_ckpt(ckpt_id, pr: gr.Request):
                show_output = ckpt_list_info.update(visible=True)
                if not ckpt_id:
                    message = "Please select one checkpoint to delete."
                else:
                    message = api_manager.ckpts_delete(ckpts=[ckpt_id], user_token=pr.username)
                return show_output, message, ''

            delete_ckpt_btn = gr.Button(value='Delete \U0001F5D1', elem_id="delete_ckpt")
            delete_ckpt_btn.click(fn=_delete_ckpt,
                                  inputs=[ckpt_list_selected],
                                  outputs=[ckpt_list_info, ckpt_list_info, ckpt_list_selected])
            # ---- bind functions end ----

    return upload_tab, model_list


def ep_create_tab():
    with (gr.Column() as sagemaker_tab):
        gr.HTML(value="<b>Deploy New SageMaker Endpoint</b>")

        with gr.Column(variant="panel", scale=1):
            default_table = f"""
                        <table style="width:100%; border: 1px solid black; border-collapse: collapse;">
                          <tr>
                            <th style="border: 1px solid grey; padding: 15px; text-align: left; " colspan="2">Default SageMaker Endpoint Config</th>
                          </tr>
                          <tr>
                            <td style="border: 1px solid grey; padding: 15px; text-align: left;"><b>Endpoint Type</b></td>
                            <td style="border: 1px solid grey; padding: 15px; text-align: left;">Async</td>
                          </tr>
                          <tr>
                            <td style="border: 1px solid grey; padding: 15px; text-align: left;"><b>Instance Type</b></td>
                            <td style="border: 1px solid grey; padding: 15px; text-align: left;">{inference_choices_default}</td>
                          </tr>
                          <tr>
                            <td style="border: 1px solid grey; padding: 15px; text-align: left;"><b>Max Instance Count</b></td>
                            <td style="border: 1px solid grey; padding: 15px; text-align: left;">1</td>
                          </tr>
                          <tr>
                            <td style="border: 1px solid grey; padding: 15px; text-align: left;"><b>Enable Autoscaling</b></td>
                            <td style="border: 1px solid grey; padding: 15px; text-align: left;">yes(range: 0 to 1)</td>
                          </tr>
                        
                        </table>
                    """
            gr.HTML(value=default_table)

            with gr.Row():
                user_roles = gr.Dropdown(choices=roles(cloud_auth_manager.username), multiselect=True,
                                         label="User Role (Required)")
                create_refresh_button_by_user(
                    user_roles,
                    lambda *args: None,
                    lambda username: {
                        'choices': roles(username)
                    },
                    'refresh_sagemaker_user_roles'
                )
            with gr.Column():
                endpoint_advance_config_enabled = gr.Checkbox(
                    label="Advanced Endpoint Configuration", value=False, visible=True
                )
            with gr.Column(visible=False) as filter_row:
                with gr.Row():
                    endpoint_name_textbox = gr.Textbox(value="", lines=1, placeholder="custom endpoint name",
                                                       label="Endpoint Name (Optional)", visible=True)
                    endpoint_type_dropdown = gr.Dropdown(label="Endpoint Type", choices=endpoint_type_choices,
                                                         elem_id="sagemaker_inference_endpoint_type_textbox",
                                                         value="Async")
                    instance_type_dropdown = gr.Dropdown(label="Instance Type", choices=inference_choices,
                                                         elem_id="sagemaker_inference_instance_type_textbox",
                                                         value=inference_choices_default)
                    instance_count_dropdown = gr.Number(label="Max Instance Number",
                                                        elem_id="sagemaker_inference_instance_count_textbox",
                                                        value=1, minimum=1, maximum=1000, step=1
                                                        )
                with gr.Column():
                    with gr.Row():
                        autoscaling_enabled = gr.Checkbox(
                            label="Enable Autoscaling",
                            value=True,
                            visible=True,
                        )
                    with gr.Row(visible=True) as autoscaling_enabled_filter_row:
                        min_instance_number_dropdown = gr.Number(value=0, label="Min Instance Number", minimum=0,
                                                                 visible=True)
                custom_extensions = gr.Textbox(
                    value="",
                    lines=5,
                    placeholder="https://github.com/awslabs/stable-diffusion-aws-extension.git#main#a096556799b7b0686e19ec94c0dbf2ca74d8ffbc",
                    label=f"Custom Extension URLs (Optional) - Please separate with line breaks",
                    visible=False,
                    info="The endpoint will set an environment variable named EXTENSIONS, default image will be install automatically."
                )

                custom_docker_image_uri = gr.Textbox(
                    value="",
                    lines=1,
                    placeholder="123456789.dkr.ecr.us-east-1.amazonaws.com/repo/image:latest",
                    label=f"Custom Docker Image URI (Optional)",
                    visible=False,
                    info="The endpoint will be deployed with your custom docker image."
                )

            ep_deploy_btn = gr.Button(value="Deploy Endpoint", variant='primary',
                                                elem_id="sagemaker_deploy_endpoint_button")
            ep_create_info = gr.Textbox(interactive=False, show_label=False, visible=True)

            def _create_sagemaker_endpoint(endpoint_name,
                                           endpoint_type,
                                           instance_type,
                                           scale_count,
                                           autoscale,
                                           docker_image_uri,
                                           custom_extensions,
                                           target_user_roles,
                                           min_instance_number,
                                           pr: gr.Request):
                if not target_user_roles:
                    message = "Please select at least one user role."
                else:
                    message = api_manager.sagemaker_deploy(endpoint_name=endpoint_name,
                                                           endpoint_type=endpoint_type,
                                                           instance_type=instance_type,
                                                           initial_instance_count=scale_count,
                                                           custom_docker_image_uri=docker_image_uri,
                                                           custom_extensions=custom_extensions,
                                                           autoscaling_enabled=autoscale,
                                                           user_roles=target_user_roles,
                                                           min_instance_number=min_instance_number,
                                                           username=pr.username
                                                           )
                return ep_create_info.update(value=message, visible=True)

            ep_deploy_btn.click(fn=_create_sagemaker_endpoint,
                                inputs=[endpoint_name_textbox,
                                        endpoint_type_dropdown,
                                        instance_type_dropdown,
                                        instance_count_dropdown,
                                        autoscaling_enabled,
                                        custom_docker_image_uri,
                                        custom_extensions,
                                        user_roles,
                                        min_instance_number_dropdown,
                                        ],
                                outputs=[ep_create_info])

        def toggle_new_rows(checkbox_state):
            show_byoc = False
            if checkbox_state:
                username = cloud_auth_manager.username
                user = api_manager.get_user_by_username(username=username, h_username=username)
                if 'roles' in user:
                    show_byoc = 'byoc' in user['roles']
            return gr.update(visible=checkbox_state), custom_docker_image_uri.update(
                visible=show_byoc), custom_extensions.update(visible=show_byoc)

        def toggle_autoscaling_enabled_rows(checkbox_state):
            if checkbox_state:
                return gr.update(visible=True)
            else:
                return gr.update(visible=False)

        def endpoint_type_dropdown_change(endpoint_type):
            if endpoint_type == "Real-time":
                return gr.update(value=1, minimum=1)
            else:
                return gr.update(value=0, minimum=0)

        endpoint_type_dropdown.change(
            fn=endpoint_type_dropdown_change,
            inputs=[endpoint_type_dropdown],
            outputs=[min_instance_number_dropdown]
        )

        endpoint_advance_config_enabled.change(
            fn=toggle_new_rows,
            inputs=endpoint_advance_config_enabled,
            outputs=[filter_row, custom_docker_image_uri, custom_extensions]
        )

        autoscaling_enabled.change(
            fn=toggle_autoscaling_enabled_rows,
            inputs=autoscaling_enabled,
            outputs=[autoscaling_enabled_filter_row]
        )

        return sagemaker_tab


def _list_sagemaker_endpoints(username):
    resp = api_manager.list_all_sagemaker_endpoints_raw(username=username, user_token=username)
    endpoints = []
    for endpoint in resp:
        if 'endpoint_type' not in endpoint or not endpoint['endpoint_type']:
            endpoint['endpoint_type'] = 'Async'
        if 'owner_group_or_role' in endpoint and endpoint['owner_group_or_role']:
            endpoint_roles = ','.join(endpoint['owner_group_or_role'])

            scale_scope = ""
            min_instance_number = endpoint['min_instance_number'] if 'min_instance_number' in endpoint and endpoint[
                'min_instance_number'] else "0"
            max_instance_number = endpoint['max_instance_number'] if 'max_instance_number' in endpoint and endpoint[
                'max_instance_number'] else ""
            if max_instance_number:
                scale_scope = f"({min_instance_number}-{max_instance_number})"

            autoscaling = endpoint['autoscaling']
            if autoscaling:
                autoscaling = f"yes {scale_scope}"

            endpoints.append([
                endpoint['endpoint_name'],
                endpoint['endpoint_type'],
                endpoint_roles,
                autoscaling,
                endpoint['endpoint_status'],
                endpoint['current_instance_count'] if endpoint['current_instance_count'] else "0",
                endpoint['instance_type'] if endpoint['instance_type'] else "",
                endpoint['startTime'].split(' ')[0] if endpoint['startTime'] else "",
            ])

    if len(endpoints) == 0:
        endpoints = [['', '', '', '', '', '', '', '']]

    return endpoints


def _list_trainings_job(username):
    jobs = []
    items = api_manager.list_all_train_jobs_raw(username=username)

    for item in items:
        output_name = ""

        try:
            output_name = item['params']['config_params']['saving_arguments']['output_name']
        except Exception as e:
            pass

        jobs.append([
            item['id'],
            item['sagemakerTrainName'],
            output_name,
            item['modelName'],
            item['status'],
            item['trainType'],
        ])

    if len(jobs) == 0:
        jobs = [['', '', '', '', '', '']]

    return jobs


def _list_trainings_job_for_delete(username):
    jobs = []
    items = api_manager.list_all_train_jobs_raw(username=username)
    for item in items:
        jobs.append(item['id'])
    return jobs


def ep_list_tab():
    with gr.Column(scale=2):
        gr.HTML(value="<b>Sagemaker Endpoints List</b>")

        ep_list = gr.Dataframe(
            headers=['Name', 'Type', 'Owners', 'Autoscaling', 'Status', 'Instance', 'Instance Type', 'Created Time'],
            datatype=['str', 'str', 'str', 'str', 'str', 'str', 'str', 'str'],
            interactive=False,
        )

        with gr.Row():
            ep_list_prev_btn = gr.Button(value='Previous Page', elem_id="sagemaker_endpoint_list_prev_btn")
            ep_list_next_btn = gr.Button(value='Next Page', elem_id="sagemaker_endpoint_list_next_btn")
            ep_delete_btn = gr.Button(value='Delete \U0001F5D1', elem_id="sagemaker_endpoint_delete_btn")

        with gr.Row():
            ep_list_info = gr.Textbox(value="", show_label=False, interactive=False, visible=False)
            ep_selected = gr.Textbox(value="", label="Selected Endpoint item", visible=False)

        # ----- events and bind functions start -----
        def list_ep_prev(rq: gr.Request):
            result = _list_sagemaker_endpoints(rq.username)
            return result, '', ep_list_info.update(value="", visible=False)

        def list_ep_next(rq: gr.Request):
            result = _list_sagemaker_endpoints(rq.username)
            return result, '', ep_list_info.update(value="", visible=False)

        def choose_ep(evt: gr.SelectData, dataset):
            row_index = evt.index[0]
            ep_name = dataset.values[row_index][0]
            if ep_name:
                message = f"You selected endpoint is: {ep_name}"
                visible = True
            else:
                message = ""
                visible = False
                ep_name = ""
            return ep_list_info.update(value=message, visible=visible), ep_name
        ep_list.select(fn=choose_ep, inputs=[ep_list], outputs=[ep_list_info, ep_selected])

        ep_list_next_btn.click(fn=list_ep_next, inputs=[], outputs=[ep_list, ep_selected, ep_list_info])
        ep_list_prev_btn.click(fn=list_ep_prev, inputs=[], outputs=[ep_list, ep_selected, ep_list_info])

        def delete_ep(ep, rq: gr.Request):
            new_list = _list_sagemaker_endpoints(rq.username)
            if not ep:
                message = 'No endpoint selected'
            else:
                message = api_manager.sagemaker_endpoint_delete(delete_endpoint_list=[ep], username=rq.username)
            return ep_list_info.update(value=message, visible=True), '', new_list

        ep_delete_btn.click(fn=delete_ep, inputs=[ep_selected], outputs=[ep_list_info, ep_selected, ep_list])
        # ----- events and bind functions end -----

        return ep_list


def dataset_tab():
    with gr.Row() as dt:
        with gr.Column(variant='panel'):
            gr.HTML(value="<u><b>Create a Dataset</b></u>")

            def upload_file(files):
                file_paths = [file.name for file in files]
                return file_paths

            file_output = gr.File()
            upload_button = gr.UploadButton("Click to Upload Files",
                                            file_types=["image", "video", "text"],
                                            file_count="multiple")
            upload_button.upload(fn=upload_file, inputs=[upload_button], outputs=[file_output])

            def create_dataset(files, dataset_name, dataset_prefix, dataset_desc, pr: gr.Request):
                if not files:
                    message = 'No files selected'
                    return dataset_create_result.update(value=message, visible=True), None, None, None, None
                if not dataset_name:
                    message = 'No dataset name'
                    return dataset_create_result.update(value=message, visible=True), None, None, None, None
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
                    "prefix": dataset_prefix,
                    "params": {
                        "description": dataset_desc
                    },
                    "creator": pr.username
                }

                url = get_variable_from_json('api_gateway_url') + 'datasets'
                api_key = get_variable_from_json('api_token')

                if not has_config():
                    message = f'Please config api url and token'
                    return dataset_create_result.update(value=message, visible=True), None, None, None, None

                raw_response = requests.post(url=url, json=payload,
                                             headers={'x-api-key': api_key, "username": pr.username})
                logger.info(raw_response.json())

                if raw_response.status_code != 201:
                    message = f'{raw_response.json()["message"]}'
                    return dataset_create_result.update(value=message, visible=True), None, None, None, None
                response = raw_response.json()['data']

                logger.info(f"Start upload sample files response:\n{response}")
                for filename, presign_url in response['s3PresignUrl'].items():
                    file_path = file_path_lookup[filename]
                    with open(file_path, 'rb') as f:
                        response = requests.put(presign_url, f)
                        logger.info(response)
                        response.raise_for_status()

                payload = {
                    "status": "Enabled"
                }

                raw_response = requests.put(url=f"{url}/{dataset_name}", json=payload,
                                            headers={'x-api-key': api_key, "username": pr.username})
                raw_response.raise_for_status()
                logger.debug(raw_response.json())
                message = f'Complete Dataset {dataset_name} creation'
                return dataset_create_result.update(value=message, visible=True), None, None, None, None

            dataset_name_upload = gr.Textbox(value="", lines=1, placeholder="Please input dataset name",
                                             label="Dataset Name", elem_id="sd_dataset_name_textbox")
            dataset_description_upload = gr.Textbox(value="", lines=1,
                                                    placeholder="Please input dataset description",
                                                    label="Dataset Description",
                                                    elem_id="sd_dataset_description_textbox")
            dataset_prefix = gr.Textbox(value="", lines=1, placeholder="",
                                        label="Path Prefix (Optional)", elem_id="sd_dataset_prefix_textbox")
            create_dataset_button = gr.Button("Create Dataset", variant="primary",
                                              elem_id="sagemaker_dataset_create_button")
            dataset_create_result = gr.Textbox(value="", show_label=False, interactive=False, visible=False)
            create_dataset_button.click(
                fn=create_dataset,
                inputs=[upload_button, dataset_name_upload, dataset_prefix, dataset_description_upload],
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

                delete_dataset_button = ToolButton(value='\U0001F5D1', elem_id="delete_dataset_btn")
                delete_dataset_button.click(
                    _js="delete_dataset_confirm",
                    fn=delete_dataset,
                    inputs=[cloud_dataset_name],
                    outputs=[]
                )
            with gr.Row():
                dataset_s3_output = gr.Textbox(label='dataset s3 location', show_label=True, type='text')
            with gr.Row():
                dataset_des_output = gr.Textbox(label='dataset description', show_label=True, type='text')
            with gr.Row():
                dataset_gallery = gr.Gallery(
                    label="Dataset images", show_label=False, elem_id="gallery",
                    columns=3, object_fit="contain"
                )

                def get_results_from_datasets(dataset_name, pr: gr.Request):
                    resp = api_manager.get_dataset_items_from_dataset(dataset_name, pr.username)
                    dataset_items = [(item['preview_url'], item['key']) for item in
                                     resp['data']]
                    return resp['s3'], resp['description'], dataset_items

                cloud_dataset_name.select(fn=get_results_from_datasets, inputs=[cloud_dataset_name],
                                          outputs=[dataset_s3_output, dataset_des_output, dataset_gallery])

    return dt


def trainings_tab():
    with gr.Row():
        with gr.Column(variant='panel', scale=1):
            gr.HTML(value="<u><b>Create a Training Job</b></u>")
            with gr.Row():
                train_type = gr.Dropdown(label="Train Type", choices=["Lora"], value="Lora")
                lora_train_type = gr.Dropdown(label="Train Method", choices=["kohya"], value="kohya")
            with gr.Row():
                training_instance_types = ["ml.g5.2xlarge", "ml.g5.4xlarge"]
                training_instance_type = gr.Dropdown(label="Training Instance Type", choices=training_instance_types,
                                                     value="ml.g5.2xlarge")
                fm_type = gr.Dropdown(label="FM Type", choices=["sd_1_5", "sd_xl"], value="sd_1_5")
            with gr.Row():
                model_name = gr.Dropdown(label="Model", choices=[], elem_id='train_model_dp')
                refresh_button = ToolButton(value='\U0001f504', elem_id='train_model_name')

                def refresh_model_name(rq: gr.Request):
                    choices = list(set([model['name'] for model in api_manager.list_models_on_cloud(rq.username)]))
                    return model_name.update(choices=choices)

                refresh_button.click(
                    fn=refresh_model_name,
                    inputs=[],
                    outputs=[model_name]
                )

            with gr.Row():
                dataset_name = gr.Dropdown(label="Dataset", choices=[], elem_id='train_dataset_dp')
                refresh_dt_button = ToolButton(value='\U0001f504', elem_id='train_dataset_name')

                def refresh_dt_name(rq: gr.Request):
                    choices = [ds['datasetName'] for ds in get_sorted_cloud_dataset(rq.username)]
                    return dataset_name.update(choices=choices)

                refresh_dt_button.click(
                    fn=refresh_dt_name,
                    inputs=[],
                    outputs=[dataset_name]
                )

            default_config = {
                "saving_arguments": {
                    "output_name": "model_name",
                    "save_every_n_epochs": 1000
                },
                "training_arguments": {
                    "max_train_epochs": 100
                }
            }
            config_params = gr.TextArea(value=json.dumps(default_config, indent=4), label="config_params",
                                        elem_id="config_params")

            with gr.Row():
                format_config_params = gr.Button("Format Config Params")
                create_train_button = gr.Button("Create Training Job", variant="primary")
            with gr.Row():
                train_create_result = gr.Textbox(value="", show_label=False, interactive=False, visible=True)

            def create_train(lora_train_type, training_instance_type, fm_type, model_name, dataset_name,
                             config_params, rq: gr.Request):
                data = {
                    "lora_train_type": lora_train_type,
                    "params": {
                        "training_params": {
                            "training_instance_type": training_instance_type,
                            "model": model_name,
                            "dataset": dataset_name,
                            "fm_type": fm_type
                        },
                        "config_params": json.loads(config_params)
                    }
                }
                api.set_username(rq.username)

                if not has_config():
                    return [], 'Please config api url and token first'

                resp = api.create_training_job(data=data)
                return train_create_result.update(value=resp.json()['message'], visible=True)

            format_config_params.click(fn=lambda x: json.dumps(json.loads(x), indent=4), inputs=[config_params],
                                       outputs=[config_params])
            create_train_button.click(fn=create_train,
                                      inputs=[lora_train_type, training_instance_type, fm_type, model_name,
                                              dataset_name, config_params],
                                      outputs=[train_create_result])

        with gr.Column(scale=2):
            with gr.Row():
                with gr.Column(variant='panel'):
                    gr.HTML(value="<u><b>Trainings List</b></u>")

                    with gr.Row():
                        train_list = gr.Dataframe(
                            headers=['id', 'sagemakerTrainName', 'output_name', 'modelName', 'status', 'trainType'],
                            datatype=['str', 'str', 'str', 'str', 'str', 'str'],
                            interactive=False,
                        )

                        def list_ep_first(rq: gr.Request):
                            result = _list_trainings_job(rq.username)
                            return result, train_list_info.update(value="", visible=False), ""

                        def list_ep_prev(rq: gr.Request):
                            result = _list_trainings_job(rq.username)
                            return result, train_list_info.update(value="", visible=False), ""

                        def list_ep_next(rq: gr.Request):
                            result = _list_trainings_job(rq.username)
                            return result, train_list_info.update(value="", visible=False), ""

                    with gr.Row():
                        t_list_load_btn = gr.Button(value='First Page')
                        t_list_prev_btn = gr.Button(value='Previous Page')
                        t_list_next_btn = gr.Button(value='Next Page')
                        train_delete_btn = gr.Button(value='Delete \U0001F5D1')
                    with gr.Row():
                        train_list_info = gr.Textbox(value="", show_label=False, interactive=False, visible=False)
                        train_selected = gr.Textbox(value="", label="Selected Training item", visible=False)

                        t_list_load_btn.click(fn=list_ep_first, inputs=[],
                                              outputs=[train_list, train_list_info, train_selected])
                        t_list_next_btn.click(fn=list_ep_next, inputs=[],
                                              outputs=[train_list, train_list_info, train_selected])
                        t_list_prev_btn.click(fn=list_ep_prev, inputs=[],
                                              outputs=[train_list, train_list_info, train_selected])

                        def choose_training(evt: gr.SelectData, dataset):
                            row_index = evt.index[0]
                            train_id = dataset.values[row_index][0]
                            if train_id:
                                message = f"You selected training is: {train_id}"
                                visible = True
                            else:
                                train_id = ""
                                message = ""
                                visible = False
                            return train_list_info.update(value=message, visible=visible), train_id

                        train_list.select(fn=choose_training,
                                          inputs=[train_list],
                                          outputs=[train_list_info, train_selected])

                        def _train_delete(train, pr: gr.Request):
                            new_train_list = _list_trainings_job(pr.username)
                            if not train:
                                message = 'Please select a training job to delete'
                            else:
                                message = api_manager.trains_delete(list=[train], username=pr.username)
                            return train_list_info.update(value=message, visible=True), "", new_train_list

                        train_delete_btn.click(_train_delete,
                                               inputs=[train_selected],
                                               outputs=[train_list_info, train_selected, train_list])

    return train_list


def delete_dataset(selected_value):
    logger.debug(f"selected value is {selected_value}")
    if selected_value:
        if selected_value == 'cancelled':
            return
        resp = api.delete_datasets(data={
            "dataset_name_list": [selected_value],
        })
        if resp.status_code != 204:
            gr.Error(f"Error deleting dataset: {resp.json()['message']}")
        gr.Info(f"{selected_value} deleted successfully")
    else:
        gr.Warning('Please select a dataset to delete')


def test_aws_connect_config(api_url, api_token):
    if not api_url.endswith('/'):
        api_url += '/'
    target_url = f'{api_url}ping'
    headers = {
        "x-api-key": api_token,
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(target_url,
                                headers=headers)  # Assuming sagemaker_ui.server_request is a wrapper around requests
        response.raise_for_status()  # Raise an exception if the HTTP request resulted in an error
        return response.json()['message'] == 'pong'
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get server request. Details: {e}")
        return False
