from queue import Queue
import importlib
import logging
import gradio as gr
import os
import threading
import time
import utils
from aws_extension.cloud_infer_service.simple_sagemaker_infer import SimpleSagemakerInfer
import modules.scripts as scripts
from aws_extension.sagemaker_ui import None_Option_For_On_Cloud_Model, load_model_list, load_controlnet_list, load_xyz_controlnet_list
from modules import script_callbacks, sd_models, processing, extra_networks, shared
from modules.api.models import StableDiffusionTxt2ImgProcessingAPI, StableDiffusionImg2ImgProcessingAPI
from modules.sd_hijack import model_hijack
from modules.processing import Processed
from modules.shared import cmd_opts, opts
from aws_extension import sagemaker_ui

from aws_extension.cloud_models_manager.sd_manager import CloudSDModelsManager
from aws_extension.inference_scripts_helper.scripts_processor import process_args_by_plugin
from aws_extension.sagemaker_ui_tab import on_ui_tabs
from aws_extension.sagemaker_ui_utils import on_after_component_callback
from modules.ui_components import ToolButton
from scripts import global_state
from scripts.xyz_grid import list_to_csv_string, csv_string_to_list_strip

logger = logging.getLogger(__name__)
logger.setLevel(utils.LOGGING_LEVEL)
CONTROLNET_MODEL_COUNT = 3

IMG_XYZ_CHECKPOINT_INDEX = 10
TXT_XYZ_CHECKPOINT_INDEX = 11

IMG_XYZ_REFINER_CHECKPOINT_INDEX = 34
TXT_XYZ_REFINER_CHECKPOINT_INDEX = 35

IMG_XYZ_VAE_INDEX = 26
TXT_XYZ_VAE_INDEX = 27

IMG_XYZ_CONTROLNET_INDEX = 38
TXT_XYZ_CONTROLNET_INDEX = 39

TXT_SCRIPT_IDX = 2
IMG_SCRIPT_IDX = 7


def dummy_function(*args, **kwargs):
    return []


class SageMakerUI(scripts.Script):
    latest_result = None
    current_inference_id = None
    inference_queue = Queue(maxsize=30)
    default_images_inner = None
    txt2img_generate_btn = None
    img2img_generate_btn = None
    sd_model_manager = CloudSDModelsManager()
    infer_manager = SimpleSagemakerInfer()

    refresh_sd_model_checkpoint_btn = None
    setting_sd_model_checkpoint_dropdown = None

    txt2img_refiner_ckpt_dropdown = None
    txt2img_refiner_ckpt_refresh_btn = None
    img2img_refiner_ckpt_dropdown = None
    img2img_refiner_ckpt_refresh_btn = None

    txt2img_model_on_cloud = None
    img2img_model_on_cloud = None

    # todo: we don't need two of them, save one api call
    txt2img_lora_and_hypernet_models_state = None
    img2img_lora_and_hypernet_models_state = None

    # controlnet models count
    max_cn_models = shared.opts.data.get("control_net_unit_count", CONTROLNET_MODEL_COUNT)

    xyz_components = {
        'txt2img_xyz_type_x_dropdown': None,
        'txt2img_xyz_type_y_dropdown': None,
        'txt2img_xyz_type_z_dropdown': None,
        'img2img_xyz_type_x_dropdown': None,
        'img2img_xyz_type_y_dropdown': None,
        'img2img_xyz_type_z_dropdown': None,
        'txt2img_xyz_value_x_dropdown': None,
        'txt2img_xyz_value_y_dropdown': None,
        'txt2img_xyz_value_z_dropdown': None,
        'img2img_xyz_value_x_dropdown': None,
        'img2img_xyz_value_y_dropdown': None,
        'img2img_xyz_value_z_dropdown': None,
        'txt2img_xyz_value_x_textbox': None,
        'txt2img_xyz_value_y_textbox': None,
        'txt2img_xyz_value_z_textbox': None,
        'img2img_xyz_value_x_textbox': None,
        'img2img_xyz_value_y_textbox': None,
        'img2img_xyz_value_z_textbox': None,
        'xyz_grid_fill_x_tool_button': None,
        'xyz_grid_fill_y_tool_button': None,
        'xyz_grid_fill_z_tool_button': None,
        'img_xyz_grid_fill_x_tool_button': None,
        'img_xyz_grid_fill_y_tool_button': None,
        'img_xyz_grid_fill_z_tool_button': None,
        'txt2img_xyz_csv_mode': None,
        'img2img_xyz_csv_mode': None
    }

    xyz_set_components = {}

    ph = None

    controlnet_components = {
        'txt2img_controlnet_dropdown_batch': [None] * 10,
        'img2img_controlnet_dropdown_batch': [None] * 10,
        'txt2img_controlnet_refresh_btn_batch': [None] * 10,
        'img2img_controlnet_refresh_btn_batch': [None] * 10,
        'txt2img_controlnet_type_filter_radio_batch': [None] * 10,
        'img2img_controlnet_type_filter_radio_batch': [None] * 10,
    }

    def title(self):
        return "SageMaker embeddings"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def after_component(self, component, **kwargs):
        if type(component) is gr.Button:
            if self.is_txt2img and getattr(component, 'elem_id', None) == 'txt2img_generate':
                self.txt2img_generate_btn = component
            elif self.is_img2img and getattr(component, 'elem_id', None) == 'img2img_generate':
                self.img2img_generate_btn = component

        base_model_component = self.txt2img_model_on_cloud if self.is_txt2img else self.img2img_model_on_cloud
        cn_list = self.txt2img_lora_and_hypernet_models_state if self.is_txt2img else self.img2img_lora_and_hypernet_models_state
        component_elem_id = getattr(component, 'elem_id', '')
        type_pre_str = ('txt2img' if self.is_txt2img else 'img2img')
        if type(component) is gr.Dropdown:
            # refiner models
            if component_elem_id == f'{type_pre_str}_checkpoint':
                if self.is_txt2img:
                    self.txt2img_refiner_ckpt_dropdown = component
                if self.is_img2img:
                    self.img2img_refiner_ckpt_dropdown = component
            # xyz-grid type
            elif component_elem_id == f'script_{type_pre_str}_xyz_plot_x_type':
                if self.is_txt2img:
                    self.xyz_components['txt2img_xyz_type_x_dropdown'] = component
                else:
                    self.xyz_components['img2img_xyz_type_x_dropdown'] = component
            elif component_elem_id == f'script_{type_pre_str}_xyz_plot_y_type':
                if self.is_txt2img:
                    self.xyz_components['txt2img_xyz_type_y_dropdown'] = component
                else:
                    self.xyz_components['img2img_xyz_type_y_dropdown'] = component
            elif component_elem_id == f'script_{type_pre_str}_xyz_plot_z_type':
                if self.is_txt2img:
                    self.xyz_components['txt2img_xyz_type_z_dropdown'] = component
                else:
                    self.xyz_components['img2img_xyz_type_z_dropdown'] = component
            elif getattr(component, 'label', '') == 'X values':
                if self.is_txt2img:
                    self.xyz_components['txt2img_xyz_value_x_dropdown'] = component
                else:
                    self.xyz_components['img2img_xyz_value_x_dropdown'] = component
            elif getattr(component, 'label', '') == 'Y values':
                if self.is_txt2img:
                    self.xyz_components['txt2img_xyz_value_y_dropdown'] = component
                else:
                    self.xyz_components['img2img_xyz_value_y_dropdown'] = component
            elif getattr(component, 'label', '') == 'Z values':
                if self.is_txt2img:
                    self.xyz_components['txt2img_xyz_value_z_dropdown'] = component
                else:
                    self.xyz_components['img2img_xyz_value_z_dropdown'] = component

        if type(component) is gr.Textbox:
            if component_elem_id == f'script_{type_pre_str}_xyz_plot_x_values':
                if self.is_txt2img:
                    self.xyz_components['txt2img_xyz_value_x_textbox'] = component
                else:
                    self.xyz_components['img2img_xyz_value_x_textbox'] = component
            elif component_elem_id == f'script_{type_pre_str}_xyz_plot_y_values':
                if self.is_txt2img:
                    self.xyz_components['txt2img_xyz_value_y_textbox'] = component
                else:
                    self.xyz_components['img2img_xyz_value_y_textbox'] = component
            elif component_elem_id == f'script_{type_pre_str}_xyz_plot_z_values':
                if self.is_txt2img:
                    self.xyz_components['txt2img_xyz_value_z_textbox'] = component
                else:
                    self.xyz_components['img2img_xyz_value_z_textbox'] = component

        if type(component) is ToolButton:
            elem_id = ('txt2img_' if self.is_txt2img else 'img2img_') + 'checkpoint_refresh'
            if component_elem_id == elem_id:
                if self.is_txt2img:
                    self.txt2img_refiner_ckpt_refresh_btn = component
                if self.is_img2img:
                    self.img2img_refiner_ckpt_refresh_btn = component
            elif component_elem_id == 'xyz_grid_fill_x_tool_button':
                if self.is_txt2img:
                    self.xyz_components['xyz_grid_fill_x_tool_button'] = component
                else:
                    self.xyz_components['img_xyz_grid_fill_x_tool_button'] = component
            elif component_elem_id == 'xyz_grid_fill_y_tool_button':
                if self.is_txt2img:
                    self.xyz_components['xyz_grid_fill_y_tool_button'] = component
                else:
                    self.xyz_components['img_xyz_grid_fill_y_tool_button'] = component
            elif component_elem_id == 'xyz_grid_fill_z_tool_button':
                if self.is_txt2img:
                    self.xyz_components['xyz_grid_fill_z_tool_button'] = component
                else:
                    self.xyz_components['img_xyz_grid_fill_z_tool_button'] = component

        if type(component) is gr.Checkbox and getattr(component, 'elem_id', '') == f'script_{type_pre_str}_xyz_plot_csv_mode':
            if self.is_txt2img:
                self.xyz_components['txt2img_xyz_csv_mode'] = component
            else:
                self.xyz_components['img2img_xyz_csv_mode'] = component

        # controlnet models and refresh button
        # controlnet refresh button type is not webui ToolButton, maybe there is no controlnet, so use str not class

        elem_id_tabname = ("img2img" if self.is_img2img else "txt2img") + "_controlnet"
        cn_component_type = ''
        cn_elem_id_postfix = ''
        is_cn_component = False
        if type(component) is gr.Dropdown and component_elem_id and component_elem_id.endswith('_controlnet_model_dropdown'):
            cn_component_type = 'dropdown'
            cn_elem_id_postfix = 'model_dropdown'
            is_cn_component = True

        # latest controlnet has changed it's implementation, so we do both here
        if (str(type(component)) == "<class 'scripts.controlnet_ui.tool_button.ToolButton'>"
                or str(type(component)) == "<class 'scripts.controlnet_ui.controlnet_ui_group.ToolButton'>") \
                and component_elem_id and component_elem_id.endswith('_controlnet_refresh_models'):
            cn_component_type = 'refresh_btn'
            cn_elem_id_postfix = 'refresh_models'
            is_cn_component = True

        if type(component) is gr.Radio and component_elem_id and component_elem_id.endswith('_controlnet_type_filter_radio'):
            cn_component_type = cn_elem_id_postfix = 'type_filter_radio'
            is_cn_component = True

        if is_cn_component:
            if self.max_cn_models > 1:
                for i in range(self.max_cn_models):
                    tabname = f"ControlNet-{i}"
                    elem_id_controlnet = f"{elem_id_tabname}_{tabname}_controlnet_{cn_elem_id_postfix}"
                    if component_elem_id == elem_id_controlnet:
                        self.controlnet_components[f'{elem_id_tabname}_{cn_component_type}_batch'][i] = [component, False]
                        break
            else:
                tabname = "ControlNet"
                elem_id_controlnet = f"{elem_id_tabname}_{tabname}_controlnet_{cn_elem_id_postfix}"
                if component_elem_id == elem_id_controlnet:
                    self.controlnet_components[f'{elem_id_tabname}_{cn_component_type}_batch'][0] = [component, False]

        cn_txt2img_or_img2img = ('txt2img' if self.is_txt2img else 'img2img')

        base_model_component = self.txt2img_model_on_cloud if self.is_txt2img else self.img2img_model_on_cloud
        cn_list = self.txt2img_lora_and_hypernet_models_state if self.is_txt2img else self.img2img_lora_and_hypernet_models_state

        self.detector_xyz_func(base_model_component, cn_list)

        for i in range(self.max_cn_models):
            if self.controlnet_components[f'{cn_txt2img_or_img2img}_controlnet_dropdown_batch'][i] \
                    and self.controlnet_components[f'{cn_txt2img_or_img2img}_controlnet_refresh_btn_batch'][i] \
                    and self.controlnet_components[f'{cn_txt2img_or_img2img}_controlnet_type_filter_radio_batch'][i] \
                    and cn_list \
                    and base_model_component:

                def _check_cn(model_state, model_selected, k):
                    logger.debug('load')
                    on_cloud = model_selected and model_selected != None_Option_For_On_Cloud_Model
                    if not on_cloud:
                        return gr.skip()
                    controlnet_model_list = model_state['controlnet']
                    # controlnet_model_list = sagemaker_ui.load_controlnet_list(pr.username, pr.username)
                    original_dict = [('None', None)]
                    for item in controlnet_model_list:
                        if item == 'None':
                            continue
                        key = item[:item.rfind('.')]
                        original_dict.append((key, ''))
                    from collections import OrderedDict
                    new_ordered_dict = OrderedDict(original_dict)
                    # logger.debug(f'{new_ordered_dict} new_ordered_dict')
                    global_state.cn_models = new_ordered_dict
                    cn_models = global_state.select_control_type(k)
                    modified_result = list(cn_models)
                    modified_result[1] = list(new_ordered_dict.keys())
                    return gr.update(choices=cn_models[1], value=cn_models[3])

                cn_radio_tuple = self.controlnet_components[f'{cn_txt2img_or_img2img}_controlnet_type_filter_radio_batch'][i]
                if cn_radio_tuple[1]:
                    continue

                cn_radio_tuple[0] \
                    .change(fn=_check_cn,
                            inputs=[
                                cn_list,
                                base_model_component,
                                cn_radio_tuple[0]],
                            outputs=[
                                self.controlnet_components[f'{cn_txt2img_or_img2img}_controlnet_dropdown_batch'][i][0]
                            ])
                self.controlnet_components[f'{cn_txt2img_or_img2img}_controlnet_refresh_btn_batch'][i][0] \
                    .click(fn=_check_cn,
                           inputs=[
                               cn_list,
                               base_model_component,
                               cn_radio_tuple[0]],
                           outputs=[
                               self.controlnet_components[f'{cn_txt2img_or_img2img}_controlnet_dropdown_batch'][i][0]
                           ])
                cn_radio_tuple[1] = True
        pass

    def detector_xyz_func(self, base_model_component,  cn_list):

        def change_decorator(original_change, fn, inputs, outputs):
            def wrapper(*args, **kwargs):
                logger.debug("Executing extra logic before original change method")
                kwargs['fn'] = fn
                result = original_change(*args, **kwargs)
                logger.debug("Executing extra logic after original change method")
                return result

            return wrapper

        def select_axis(xyz_type_component, axis_values, axis_values_dropdown, csv_mode, model_selected, model_state):
            if not model_selected or not model_state:
                return gr.skip(), gr.skip(), gr.skip()
            logger.debug(f"_change_xyz_models {model_selected} {model_state} {xyz_type_component}")
            on_cloud = model_selected and model_selected != None_Option_For_On_Cloud_Model
            axis_options = shared.axis_options_aws
            from scripts.xyz_grid import AxisOption
            axis_options_aws = [x for x in axis_options if type(x) == AxisOption or x.is_img2img == self.is_img2img]

            choices = axis_options_aws[xyz_type_component].choices
            has_choices = choices is not None
            if not on_cloud:
                if has_choices:
                    choices = choices()
            elif self.is_txt2img and (xyz_type_component == TXT_XYZ_CHECKPOINT_INDEX
                                      or xyz_type_component == TXT_XYZ_REFINER_CHECKPOINT_INDEX):
                sd_model_list = model_state['sd']
                logger.debug(f"sd processed {sd_model_list}")
                choices = sd_model_list
                has_choices = choices is not None
            elif not self.is_txt2img and (xyz_type_component == IMG_XYZ_CHECKPOINT_INDEX
                                          or xyz_type_component == IMG_XYZ_REFINER_CHECKPOINT_INDEX):
                sd_model_list = model_state['sd']
                logger.debug(f"sd processed {sd_model_list}")
                choices = sd_model_list
                has_choices = choices is not None
            elif self.is_txt2img and xyz_type_component == TXT_XYZ_VAE_INDEX:
                vae_model_list = model_state['vae']
                logger.debug(f"vae processed {vae_model_list}")
                choices = vae_model_list
                has_choices = choices is not None
            elif not self.is_txt2img and xyz_type_component == IMG_XYZ_VAE_INDEX:
                vae_model_list = model_state['vae']
                logger.debug(f"vae processed {vae_model_list}")
                choices = vae_model_list
                has_choices = choices is not None
            elif self.is_txt2img and xyz_type_component == TXT_XYZ_CONTROLNET_INDEX:
                controlnet_model_list = model_state['controlnet_xyz']
                logger.debug(f"controlnet processed {controlnet_model_list}")
                choices = controlnet_model_list
                has_choices = choices is not None
            elif not self.is_txt2img and xyz_type_component == IMG_XYZ_CONTROLNET_INDEX:
                controlnet_model_list = model_state['controlnet_xyz']
                logger.debug(f"controlnet processed {controlnet_model_list}")
                choices = controlnet_model_list
                has_choices = choices is not None
            else:
                if has_choices:
                    choices = choices()
            if has_choices:
                if csv_mode:
                    if axis_values_dropdown:
                        axis_values = list_to_csv_string(list(filter(lambda x: x in choices, axis_values_dropdown)))
                        axis_values_dropdown = []
                else:
                    if axis_values:
                        axis_values_dropdown = list(
                            filter(lambda x: x in choices, csv_string_to_list_strip(axis_values)))
                        axis_values = ""
            return (gr.Button.update(visible=has_choices),
                    gr.Textbox.update(visible=not has_choices or csv_mode, value=axis_values),
                    gr.update(choices=choices if has_choices else None, visible=has_choices and not csv_mode,
                              value=axis_values_dropdown))

        def fill(axis_type, csv_mode, model_selected, model_state):
            if not model_selected or not model_state:
                return gr.skip(), gr.skip()
            axis_options = shared.axis_options_aws
            from scripts.xyz_grid import AxisOption
            axis_options_aws = [x for x in axis_options if type(x) == AxisOption or x.is_img2img == self.is_img2img]
            axis = axis_options_aws[axis_type]
            on_cloud = model_selected and model_selected != None_Option_For_On_Cloud_Model
            choices = axis_options_aws[axis_type].choices
            if choices:
                if not on_cloud:
                    choices = choices()
                elif self.is_txt2img and (axis_type == TXT_XYZ_CHECKPOINT_INDEX
                                          or axis_type == TXT_XYZ_REFINER_CHECKPOINT_INDEX):
                    sd_model_list = model_state['sd']
                    logger.info(f"sd processed {sd_model_list}")
                    choices = sd_model_list
                elif not self.is_txt2img and (axis_type == IMG_XYZ_CHECKPOINT_INDEX
                                              or axis_type == IMG_XYZ_REFINER_CHECKPOINT_INDEX):
                    sd_model_list = model_state['sd']
                    logger.info(f"sd processed {sd_model_list}")
                    choices = sd_model_list
                elif self.is_txt2img and axis_type == TXT_XYZ_VAE_INDEX:
                    vae_model_list = model_state['vae']
                    logger.info(f"vae processed {vae_model_list}")
                    choices = vae_model_list
                elif not self.is_txt2img and axis_type == IMG_XYZ_VAE_INDEX:
                    vae_model_list = model_state['vae']
                    logger.info(f"vae processed {vae_model_list}")
                    choices = vae_model_list
                elif self.is_txt2img and axis_type == TXT_XYZ_CONTROLNET_INDEX or axis_type == IMG_XYZ_CONTROLNET_INDEX:
                    controlnet_model_list = model_state['controlnet']
                    logger.info(f"controlnet processed {controlnet_model_list}")
                    choices = controlnet_model_list
                elif not self.is_txt2img and axis_type == IMG_XYZ_CONTROLNET_INDEX:
                    controlnet_model_list = model_state['controlnet']
                    logger.info(f"controlnet processed {controlnet_model_list}")
                    choices = controlnet_model_list
                if csv_mode:
                    return list_to_csv_string(choices), gr.update()
                else:
                    return gr.update(), choices
            else:
                return gr.update(), gr.update()

        def change_choice_mode(csv_mode, x_type, x_values, x_values_dropdown, y_type, y_values, y_values_dropdown,
                               z_type, z_values, z_values_dropdown, model_selected, model_state):
            if not model_selected or not model_state:
                return gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip()
            _fill_x_button, _x_values, _x_values_dropdown = select_axis(x_type, x_values, x_values_dropdown, csv_mode,
                                                                        model_selected, model_state)
            _fill_y_button, _y_values, _y_values_dropdown = select_axis(y_type, y_values, y_values_dropdown, csv_mode,
                                                                        model_selected, model_state)
            _fill_z_button, _z_values, _z_values_dropdown = select_axis(z_type, z_values, z_values_dropdown, csv_mode,
                                                                        model_selected, model_state)
            return _fill_x_button, _x_values, _x_values_dropdown, _fill_y_button, _y_values, _y_values_dropdown, _fill_z_button, _z_values, _z_values_dropdown

        if cn_list and base_model_component:
            if 'txt2img_xyz_type_x_dropdown' not in self.xyz_set_components and self.xyz_components[
                'txt2img_xyz_type_x_dropdown'] and self.xyz_components['txt2img_xyz_value_x_dropdown'] and \
                    self.xyz_components['txt2img_xyz_value_x_textbox'] and self.xyz_components['txt2img_xyz_csv_mode'] and \
                    self.xyz_components['xyz_grid_fill_x_tool_button']:
                self.xyz_components['txt2img_xyz_type_x_dropdown'].change(fn=select_axis, inputs=[
                    self.xyz_components['txt2img_xyz_type_x_dropdown'],
                    self.xyz_components['txt2img_xyz_value_x_textbox'],
                    self.xyz_components['txt2img_xyz_value_x_dropdown'], self.xyz_components['txt2img_xyz_csv_mode'],
                    base_model_component, cn_list], outputs=[self.xyz_components['xyz_grid_fill_x_tool_button'],
                                                             self.xyz_components['txt2img_xyz_value_x_textbox'],
                                                             self.xyz_components['txt2img_xyz_value_x_dropdown']])

                self.xyz_components['txt2img_xyz_type_x_dropdown'].change = change_decorator(
                    self.xyz_components['txt2img_xyz_type_x_dropdown'].change, fn=select_axis,
                    inputs=[self.xyz_components['txt2img_xyz_type_x_dropdown'],
                            self.xyz_components['txt2img_xyz_value_x_textbox'],
                            self.xyz_components['txt2img_xyz_value_x_dropdown'],
                            self.xyz_components['txt2img_xyz_csv_mode'], base_model_component, cn_list],
                    outputs=[self.xyz_components['xyz_grid_fill_x_tool_button'],
                             self.xyz_components['txt2img_xyz_value_x_textbox'],
                             self.xyz_components['txt2img_xyz_value_x_dropdown']])

                self.xyz_components['xyz_grid_fill_x_tool_button'].click(fn=fill, inputs=[
                    self.xyz_components['txt2img_xyz_type_x_dropdown'], self.xyz_components['txt2img_xyz_csv_mode'],
                    base_model_component, cn_list],
                                                                         outputs=[self.xyz_components[
                                                                                      'txt2img_xyz_value_x_textbox'],
                                                                                  self.xyz_components[
                                                                                      'txt2img_xyz_value_x_dropdown']])

                self.xyz_components['xyz_grid_fill_x_tool_button'].click = change_decorator(
                    self.xyz_components['xyz_grid_fill_x_tool_button'].click, fn=fill, inputs=[
                        self.xyz_components['txt2img_xyz_type_x_dropdown'], self.xyz_components['txt2img_xyz_csv_mode'],
                        base_model_component, cn_list],
                    outputs=[self.xyz_components[
                                 'txt2img_xyz_value_x_textbox'],
                             self.xyz_components[
                                 'txt2img_xyz_value_x_dropdown']])

                self.xyz_components['txt2img_xyz_csv_mode'].change(fn=change_choice_mode, inputs=[
                    self.xyz_components['txt2img_xyz_csv_mode'], self.xyz_components['txt2img_xyz_type_x_dropdown'],
                    self.xyz_components['txt2img_xyz_value_x_textbox'],
                    self.xyz_components['txt2img_xyz_value_x_dropdown'],
                    self.xyz_components['txt2img_xyz_type_y_dropdown'],
                    self.xyz_components['txt2img_xyz_value_y_textbox'],
                    self.xyz_components['txt2img_xyz_value_y_dropdown'],
                    self.xyz_components['txt2img_xyz_type_z_dropdown'],
                    self.xyz_components['txt2img_xyz_value_z_textbox'],
                    self.xyz_components['txt2img_xyz_value_z_dropdown'], base_model_component, cn_list
                ], outputs=[self.xyz_components['xyz_grid_fill_x_tool_button'],
                            self.xyz_components['txt2img_xyz_value_x_textbox'],
                            self.xyz_components['txt2img_xyz_value_x_dropdown'],
                            self.xyz_components['xyz_grid_fill_y_tool_button'],
                            self.xyz_components['txt2img_xyz_value_y_textbox'],
                            self.xyz_components['txt2img_xyz_value_y_dropdown'],
                            self.xyz_components['xyz_grid_fill_z_tool_button'],
                            self.xyz_components['txt2img_xyz_value_z_textbox'],
                            self.xyz_components['txt2img_xyz_value_z_dropdown']])

                self.xyz_components['txt2img_xyz_csv_mode'].change = change_decorator(
                    self.xyz_components['txt2img_xyz_csv_mode'].change, fn=change_choice_mode, inputs=[
                        self.xyz_components['txt2img_xyz_csv_mode'], self.xyz_components['txt2img_xyz_type_x_dropdown'],
                        self.xyz_components['txt2img_xyz_value_x_textbox'],
                        self.xyz_components['txt2img_xyz_value_x_dropdown'],
                        self.xyz_components['txt2img_xyz_type_y_dropdown'],
                        self.xyz_components['txt2img_xyz_value_y_textbox'],
                        self.xyz_components['txt2img_xyz_value_y_dropdown'],
                        self.xyz_components['txt2img_xyz_type_z_dropdown'],
                        self.xyz_components['txt2img_xyz_value_z_textbox'],
                        self.xyz_components['txt2img_xyz_value_z_dropdown'], base_model_component, cn_list
                    ], outputs=[self.xyz_components['xyz_grid_fill_x_tool_button'],
                                self.xyz_components['txt2img_xyz_value_x_textbox'],
                                self.xyz_components['txt2img_xyz_value_x_dropdown'],
                                self.xyz_components['xyz_grid_fill_y_tool_button'],
                                self.xyz_components['txt2img_xyz_value_y_textbox'],
                                self.xyz_components['txt2img_xyz_value_y_dropdown'],
                                self.xyz_components['xyz_grid_fill_z_tool_button'],
                                self.xyz_components['txt2img_xyz_value_z_textbox'],
                                self.xyz_components['txt2img_xyz_value_z_dropdown']])

                self.xyz_set_components['txt2img_xyz_type_x_dropdown'] = True
            if 'txt2img_xyz_type_y_dropdown' not in self.xyz_set_components and \
                    self.xyz_components['txt2img_xyz_type_y_dropdown'] and \
                    self.xyz_components['txt2img_xyz_value_y_dropdown'] and \
                    self.xyz_components['txt2img_xyz_value_y_textbox'] and self.xyz_components['txt2img_xyz_csv_mode'] and \
                    self.xyz_components['xyz_grid_fill_y_tool_button']:
                self.xyz_components['txt2img_xyz_type_y_dropdown'].change(fn=select_axis, inputs=[
                    self.xyz_components['txt2img_xyz_type_y_dropdown'],
                    self.xyz_components['txt2img_xyz_value_y_textbox'],
                    self.xyz_components['txt2img_xyz_value_y_dropdown'], self.xyz_components['txt2img_xyz_csv_mode'],
                    base_model_component, cn_list], outputs=[self.xyz_components['xyz_grid_fill_y_tool_button'],
                                                             self.xyz_components['txt2img_xyz_value_y_textbox'],
                                                             self.xyz_components['txt2img_xyz_value_y_dropdown']])

                self.xyz_components['txt2img_xyz_type_y_dropdown'].change = change_decorator(
                    self.xyz_components['txt2img_xyz_type_y_dropdown'].change, fn=select_axis,
                    inputs=[self.xyz_components['txt2img_xyz_type_y_dropdown'],
                            self.xyz_components['txt2img_xyz_value_y_textbox'],
                            self.xyz_components['txt2img_xyz_value_y_dropdown'],
                            self.xyz_components['txt2img_xyz_csv_mode'], base_model_component, cn_list],
                    outputs=[self.xyz_components['xyz_grid_fill_y_tool_button'],
                             self.xyz_components['txt2img_xyz_value_y_textbox'],
                             self.xyz_components['txt2img_xyz_value_y_dropdown']])

                self.xyz_components['xyz_grid_fill_y_tool_button'].click(fn=fill, inputs=[
                    self.xyz_components['txt2img_xyz_type_y_dropdown'], self.xyz_components['txt2img_xyz_csv_mode'],
                    base_model_component, cn_list],
                                                                         outputs=[self.xyz_components[
                                                                                      'txt2img_xyz_value_y_textbox'],
                                                                                  self.xyz_components[
                                                                                      'txt2img_xyz_value_y_dropdown']])

                self.xyz_components['xyz_grid_fill_y_tool_button'].click = change_decorator(
                    self.xyz_components['xyz_grid_fill_y_tool_button'].click, fn=fill, inputs=[
                        self.xyz_components['txt2img_xyz_type_y_dropdown'], self.xyz_components['txt2img_xyz_csv_mode'],
                        base_model_component, cn_list],
                    outputs=[self.xyz_components[
                                 'txt2img_xyz_value_y_textbox'],
                             self.xyz_components[
                                 'txt2img_xyz_value_y_dropdown']])

                self.xyz_set_components['txt2img_xyz_type_y_dropdown'] = True
            if 'txt2img_xyz_type_z_dropdown' not in self.xyz_set_components and self.xyz_components[
                'txt2img_xyz_type_z_dropdown'] and self.xyz_components['txt2img_xyz_value_z_dropdown'] and \
                    self.xyz_components['txt2img_xyz_value_z_textbox'] and self.xyz_components[
                'txt2img_xyz_csv_mode'] and self.xyz_components['xyz_grid_fill_z_tool_button']:
                self.xyz_components['txt2img_xyz_type_z_dropdown'].change(fn=select_axis, inputs=[
                    self.xyz_components['txt2img_xyz_type_z_dropdown'],
                    self.xyz_components['txt2img_xyz_value_z_textbox'],
                    self.xyz_components['txt2img_xyz_value_z_dropdown'], self.xyz_components['txt2img_xyz_csv_mode'],
                    base_model_component, cn_list], outputs=[self.xyz_components['xyz_grid_fill_z_tool_button'],
                                                             self.xyz_components['txt2img_xyz_value_z_textbox'],
                                                             self.xyz_components['txt2img_xyz_value_z_dropdown']])

                self.xyz_components['txt2img_xyz_type_z_dropdown'].change = change_decorator(
                    self.xyz_components['txt2img_xyz_type_z_dropdown'].change, fn=select_axis,
                    inputs=[self.xyz_components['txt2img_xyz_type_z_dropdown'],
                            self.xyz_components['txt2img_xyz_value_z_textbox'],
                            self.xyz_components['txt2img_xyz_value_z_dropdown'],
                            self.xyz_components['txt2img_xyz_csv_mode'], base_model_component, cn_list],
                    outputs=[self.xyz_components['xyz_grid_fill_z_tool_button'],
                             self.xyz_components['txt2img_xyz_value_z_textbox'],
                             self.xyz_components['txt2img_xyz_value_z_dropdown']])

                self.xyz_components['xyz_grid_fill_z_tool_button'].click(fn=fill, inputs=[
                    self.xyz_components['txt2img_xyz_type_z_dropdown'], self.xyz_components['txt2img_xyz_csv_mode'],
                    base_model_component, cn_list],
                                                                         outputs=[self.xyz_components[
                                                                                      'txt2img_xyz_value_z_textbox'],
                                                                                  self.xyz_components[
                                                                                      'txt2img_xyz_value_z_dropdown']])

                self.xyz_components['xyz_grid_fill_z_tool_button'].click = change_decorator(
                    self.xyz_components['xyz_grid_fill_z_tool_button'].click, fn=fill, inputs=[
                        self.xyz_components['txt2img_xyz_type_z_dropdown'], self.xyz_components['txt2img_xyz_csv_mode'],
                        base_model_component, cn_list],
                    outputs=[self.xyz_components[
                                 'txt2img_xyz_value_z_textbox'],
                             self.xyz_components[
                                 'txt2img_xyz_value_z_dropdown']])

                self.xyz_set_components['txt2img_xyz_type_z_dropdown'] = True
            if 'img2img_xyz_type_x_dropdown' not in self.xyz_set_components and self.xyz_components[
                'img2img_xyz_type_x_dropdown'] and self.xyz_components['img2img_xyz_value_x_dropdown'] and \
                    self.xyz_components['img2img_xyz_value_x_textbox'] and self.xyz_components[
                'img2img_xyz_csv_mode'] and self.xyz_components['img_xyz_grid_fill_x_tool_button']:
                self.xyz_components['img2img_xyz_type_x_dropdown'].change(fn=select_axis, inputs=[
                    self.xyz_components['img2img_xyz_type_x_dropdown'],
                    self.xyz_components['img2img_xyz_value_x_textbox'],
                    self.xyz_components['img2img_xyz_value_x_dropdown'], self.xyz_components['img2img_xyz_csv_mode'],
                    base_model_component, cn_list], outputs=[self.xyz_components['xyz_grid_fill_x_tool_button'],
                                                             self.xyz_components['img2img_xyz_value_x_textbox'],
                                                             self.xyz_components['img2img_xyz_value_x_dropdown']])

                self.xyz_components['img2img_xyz_type_x_dropdown'].change = change_decorator(
                    self.xyz_components['img2img_xyz_type_x_dropdown'].change, fn=select_axis,
                    inputs=[self.xyz_components['img2img_xyz_type_x_dropdown'],
                            self.xyz_components['img2img_xyz_value_x_textbox'],
                            self.xyz_components['img2img_xyz_value_x_dropdown'],
                            self.xyz_components['img2img_xyz_csv_mode'], base_model_component, cn_list],
                    outputs=[self.xyz_components['img_xyz_grid_fill_x_tool_button'],
                             self.xyz_components['img2img_xyz_value_x_textbox'],
                             self.xyz_components['img2img_xyz_value_x_dropdown']])

                self.xyz_components['img_xyz_grid_fill_x_tool_button'].click(fn=fill, inputs=[
                    self.xyz_components['img2img_xyz_type_x_dropdown'], self.xyz_components['img2img_xyz_csv_mode'],
                    base_model_component, cn_list],
                                                                             outputs=[self.xyz_components[
                                                                                          'img2img_xyz_value_x_textbox'],
                                                                                      self.xyz_components[
                                                                                          'img2img_xyz_value_x_dropdown']])

                self.xyz_components['img_xyz_grid_fill_x_tool_button'].click = change_decorator(
                    self.xyz_components['img_xyz_grid_fill_x_tool_button'].click, fn=fill, inputs=[
                        self.xyz_components['img2img_xyz_type_x_dropdown'], self.xyz_components['img2img_xyz_csv_mode'],
                        base_model_component, cn_list],
                    outputs=[self.xyz_components[
                                 'img2img_xyz_value_x_textbox'],
                             self.xyz_components[
                                 'img2img_xyz_value_x_dropdown']])

                self.xyz_components['img2img_xyz_csv_mode'].change(fn=change_choice_mode, inputs=[
                    self.xyz_components['img2img_xyz_csv_mode'], self.xyz_components['img2img_xyz_type_x_dropdown'],
                    self.xyz_components['img2img_xyz_value_x_textbox'],
                    self.xyz_components['img2img_xyz_value_x_dropdown'],
                    self.xyz_components['img2img_xyz_type_y_dropdown'],
                    self.xyz_components['img2img_xyz_value_y_textbox'],
                    self.xyz_components['img2img_xyz_value_y_dropdown'],
                    self.xyz_components['img2img_xyz_type_z_dropdown'],
                    self.xyz_components['img2img_xyz_value_z_textbox'],
                    self.xyz_components['img2img_xyz_value_z_dropdown'], base_model_component, cn_list
                ], outputs=[self.xyz_components['img_xyz_grid_fill_x_tool_button'],
                            self.xyz_components['img2img_xyz_value_x_textbox'],
                            self.xyz_components['img2img_xyz_value_x_dropdown'],
                            self.xyz_components['img_xyz_grid_fill_y_tool_button'],
                            self.xyz_components['img2img_xyz_value_y_textbox'],
                            self.xyz_components['img2img_xyz_value_y_dropdown'],
                            self.xyz_components['img_xyz_grid_fill_z_tool_button'],
                            self.xyz_components['img2img_xyz_value_z_textbox'],
                            self.xyz_components['img2img_xyz_value_z_dropdown']])

                self.xyz_components['img2img_xyz_csv_mode'].change = change_decorator(
                    self.xyz_components['img2img_xyz_csv_mode'].change, fn=change_choice_mode, inputs=[
                        self.xyz_components['img2img_xyz_csv_mode'], self.xyz_components['img2img_xyz_type_x_dropdown'],
                        self.xyz_components['img2img_xyz_value_x_textbox'],
                        self.xyz_components['img2img_xyz_value_x_dropdown'],
                        self.xyz_components['img2img_xyz_type_y_dropdown'],
                        self.xyz_components['img2img_xyz_value_y_textbox'],
                        self.xyz_components['img2img_xyz_value_y_dropdown'],
                        self.xyz_components['img2img_xyz_type_z_dropdown'],
                        self.xyz_components['img2img_xyz_value_z_textbox'],
                        self.xyz_components['img2img_xyz_value_z_dropdown'], base_model_component, cn_list
                    ], outputs=[self.xyz_components['img_xyz_grid_fill_x_tool_button'],
                                self.xyz_components['img2img_xyz_value_x_textbox'],
                                self.xyz_components['img2img_xyz_value_x_dropdown'],
                                self.xyz_components['img_xyz_grid_fill_y_tool_button'],
                                self.xyz_components['img2img_xyz_value_y_textbox'],
                                self.xyz_components['img2img_xyz_value_y_dropdown'],
                                self.xyz_components['img_xyz_grid_fill_z_tool_button'],
                                self.xyz_components['img2img_xyz_value_z_textbox'],
                                self.xyz_components['img2img_xyz_value_z_dropdown']])

                self.xyz_set_components['img2img_xyz_type_x_dropdown'] = True
            if 'img2img_xyz_type_y_dropdown' not in self.xyz_set_components and self.xyz_components[
                'img2img_xyz_type_y_dropdown'] and self.xyz_components['img2img_xyz_value_y_dropdown'] and \
                    self.xyz_components['img2img_xyz_value_y_textbox'] and self.xyz_components[
                'img2img_xyz_csv_mode'] and self.xyz_components['img_xyz_grid_fill_y_tool_button']:
                self.xyz_components['img2img_xyz_type_y_dropdown'].change = change_decorator(
                    self.xyz_components['img2img_xyz_type_y_dropdown'].change, fn=select_axis,
                    inputs=[self.xyz_components['img2img_xyz_type_y_dropdown'],
                            self.xyz_components['img2img_xyz_value_y_textbox'],
                            self.xyz_components['img2img_xyz_value_y_dropdown'],
                            self.xyz_components['img2img_xyz_csv_mode'], base_model_component, cn_list],
                    outputs=[self.xyz_components['img_xyz_grid_fill_y_tool_button'],
                             self.xyz_components['img2img_xyz_value_y_textbox'],
                             self.xyz_components['img2img_xyz_value_y_dropdown']])
                self.xyz_components['img2img_xyz_type_y_dropdown'].change(fn=select_axis, inputs=[
                    self.xyz_components['img2img_xyz_type_y_dropdown'],
                    self.xyz_components['img2img_xyz_value_y_textbox'],
                    self.xyz_components['img2img_xyz_value_y_dropdown'], self.xyz_components['img2img_xyz_csv_mode'],
                    base_model_component, cn_list], outputs=[self.xyz_components['img_xyz_grid_fill_y_tool_button'],
                                                             self.xyz_components['img2img_xyz_value_y_textbox'],
                                                             self.xyz_components['img2img_xyz_value_y_dropdown']])
                self.xyz_components['img_xyz_grid_fill_y_tool_button'].click = change_decorator(
                    self.xyz_components['img_xyz_grid_fill_y_tool_button'].click, fn=fill, inputs=[
                        self.xyz_components['img2img_xyz_type_y_dropdown'], self.xyz_components['img2img_xyz_csv_mode'],
                        base_model_component, cn_list],
                    outputs=[self.xyz_components[
                                 'img2img_xyz_value_y_textbox'],
                             self.xyz_components[
                                 'img2img_xyz_value_y_dropdown']])
                self.xyz_components['img_xyz_grid_fill_y_tool_button'].click(fn=fill, inputs=[
                    self.xyz_components['img2img_xyz_type_y_dropdown'], self.xyz_components['img2img_xyz_csv_mode'],
                    base_model_component, cn_list],
                                                                             outputs=[self.xyz_components[
                                                                                          'img2img_xyz_value_y_textbox'],
                                                                                      self.xyz_components[
                                                                                          'img2img_xyz_value_y_dropdown']])
                self.xyz_set_components['img2img_xyz_type_y_dropdown'] = True
            if 'img2img_xyz_type_z_dropdown' not in self.xyz_set_components and self.xyz_components[
                'img2img_xyz_type_z_dropdown'] and self.xyz_components['img2img_xyz_value_z_dropdown'] and \
                    self.xyz_components['img2img_xyz_value_z_textbox'] and self.xyz_components[
                'img2img_xyz_csv_mode'] and self.xyz_components['img_xyz_grid_fill_z_tool_button']:
                self.xyz_components['img2img_xyz_type_z_dropdown'].change = change_decorator(
                    self.xyz_components['img2img_xyz_type_z_dropdown'].change, fn=select_axis,
                    inputs=[self.xyz_components['img2img_xyz_type_z_dropdown'],
                            self.xyz_components['img2img_xyz_value_z_textbox'],
                            self.xyz_components['img2img_xyz_value_z_dropdown'],
                            self.xyz_components['img2img_xyz_csv_mode'], base_model_component, cn_list],
                    outputs=[self.xyz_components['img_xyz_grid_fill_z_tool_button'],
                             self.xyz_components['img2img_xyz_value_z_textbox'],
                             self.xyz_components['img2img_xyz_value_z_dropdown']])
                self.xyz_components['img2img_xyz_type_z_dropdown'].change(fn=select_axis, inputs=[
                    self.xyz_components['img2img_xyz_type_z_dropdown'],
                    self.xyz_components['img2img_xyz_value_z_textbox'],
                    self.xyz_components['img2img_xyz_value_z_dropdown'], self.xyz_components['img2img_xyz_csv_mode'],
                    base_model_component, cn_list], outputs=[self.xyz_components['img_xyz_grid_fill_z_tool_button'],
                                                             self.xyz_components['img2img_xyz_value_z_textbox'],
                                                             self.xyz_components['img2img_xyz_value_z_dropdown']])
                self.xyz_components['img_xyz_grid_fill_z_tool_button'].click = change_decorator(
                    self.xyz_components['img_xyz_grid_fill_z_tool_button'].click, fn=fill, inputs=[
                        self.xyz_components['img2img_xyz_type_z_dropdown'], self.xyz_components['img2img_xyz_csv_mode'],
                        base_model_component, cn_list],
                    outputs=[self.xyz_components[
                                 'img2img_xyz_value_z_textbox'],
                             self.xyz_components[
                                 'img2img_xyz_value_z_dropdown']])
                self.xyz_components['img_xyz_grid_fill_z_tool_button'].click(fn=fill, inputs=[
                    self.xyz_components['img2img_xyz_type_z_dropdown'], self.xyz_components['img2img_xyz_csv_mode'],
                    base_model_component, cn_list],
                                                                             outputs=[self.xyz_components[
                                                                                          'img2img_xyz_value_z_textbox'],
                                                                                      self.xyz_components[
                                                                                          'img2img_xyz_value_z_dropdown']])
                self.xyz_set_components['img2img_xyz_type_z_dropdown'] = True

    txt2img_script_runner = None
    img2img_script_runner = None

    def ui(self, is_img2img):
        def _check_generate(model_selected, pr: gr.Request):
            on_cloud = model_selected and (model_selected != None_Option_For_On_Cloud_Model or 'sd_model_checkpoint' not in opts.quicksettings_list)
            result = [f'Generate{" on Cloud" if on_cloud else ""}', gr.update(visible=not on_cloud)]
            if not on_cloud:
                result.append(gr.update(choices=sd_models.checkpoint_tiles()))
            else:
                result.append(gr.update(choices=load_model_list(pr.username, pr.username)))
            max_models = shared.opts.data.get("control_net_unit_count", CONTROLNET_MODEL_COUNT)
            if max_models > 0:
                controlnet_models = load_controlnet_list(pr.username, pr.username)
                for i in range(max_models):
                    result.append(gr.update(choices=controlnet_models))

            from modules.scripts import scripts_txt2img, scripts_img2img
            if not self.txt2img_script_runner and scripts_txt2img:
                self.txt2img_script_runner = scripts_txt2img.run

                def runner_wrapper(p, *args):
                    if on_cloud:
                        return None

                    return self.txt2img_script_runner(p, *args)

                setattr(scripts_txt2img, 'run', runner_wrapper)

            if not self.img2img_script_runner and scripts_img2img:
                self.img2img_script_runner = scripts_img2img.run

                def runner_wrapper(p, *args):
                    if on_cloud:
                        return None

                    return self.img2img_script_runner(p, *args)

                setattr(scripts_img2img, 'run', runner_wrapper)

            return result

        sagemaker_inputs_components = []
        if is_img2img:
            self.img2img_model_on_cloud, ied, sd_vae_on_cloud_dropdown, inference_job_dropdown, primary_model_name, \
            secondary_model_name, tertiary_model_name, \
            modelmerger_merge_on_cloud, self.img2img_lora_and_hypernet_models_state = sagemaker_ui.create_ui(
                is_img2img)
            outputs = [self.img2img_generate_btn, self.img2img_refiner_ckpt_refresh_btn,
                       self.img2img_refiner_ckpt_dropdown]
            for value in self.controlnet_components['img2img_controlnet_dropdown_batch']:
                if value:
                    outputs.append(value[0])

            self.img2img_model_on_cloud.change(_check_generate, inputs=self.img2img_model_on_cloud, outputs=outputs)

            if 'sd_model_checkpoint' not in opts.quicksettings_list:
                self.img2img_generate_btn.value = 'Generate on Cloud'

            sagemaker_inputs_components = [self.img2img_model_on_cloud, ied, sd_vae_on_cloud_dropdown, inference_job_dropdown,
                    primary_model_name, secondary_model_name, tertiary_model_name, modelmerger_merge_on_cloud,
                    self.img2img_lora_and_hypernet_models_state]
        else:
            self.txt2img_model_on_cloud, ied, sd_vae_on_cloud_dropdown, inference_job_dropdown, primary_model_name, \
            secondary_model_name, tertiary_model_name, \
            modelmerger_merge_on_cloud, self.txt2img_lora_and_hypernet_models_state = sagemaker_ui.create_ui(
                is_img2img)
            outputs = [self.txt2img_generate_btn, self.txt2img_refiner_ckpt_refresh_btn,
                       self.txt2img_refiner_ckpt_dropdown]
            for value in self.controlnet_components['txt2img_controlnet_dropdown_batch']:
                if value:
                    outputs.append(value[0])

            self.txt2img_model_on_cloud.change(_check_generate, inputs=self.txt2img_model_on_cloud, outputs=outputs)

            if 'sd_model_checkpoint' not in opts.quicksettings_list:
                self.txt2img_generate_btn.value = 'Generate on Cloud'

            sagemaker_inputs_components = [self.txt2img_model_on_cloud, ied, sd_vae_on_cloud_dropdown, inference_job_dropdown,
                    primary_model_name, secondary_model_name, tertiary_model_name, modelmerger_merge_on_cloud,
                    self.txt2img_lora_and_hypernet_models_state]

        return sagemaker_inputs_components

    def before_process(self, p, *args):
        on_docker = os.environ.get('ON_DOCKER', "false")
        if on_docker == "true":
            return

        # check if endpoint is InService
        sd_model_on_cloud = args[0]
        endpoint_type = args[1]
        always_on_cloud = 'sd_model_checkpoint' not in opts.quicksettings_list
        if sd_model_on_cloud == None_Option_For_On_Cloud_Model and not always_on_cloud:
            return

        models = {'Stable-diffusion': [sd_model_on_cloud]}

        api_param_cls = None
        if self.is_img2img:
            api_param_cls = StableDiffusionImg2ImgProcessingAPI

        if self.is_txt2img:
            api_param_cls = StableDiffusionTxt2ImgProcessingAPI

        if not api_param_cls:
            raise NotImplementedError

        p.sampler_index = p.sampler_name

        api_param = api_param_cls(**p.__dict__)
        if self.is_img2img:
            api_param.mask = p.image_mask

        selected_script_index = p.script_args[0] - 1
        selected_script_name = None if selected_script_index < 0 else p.scripts.selectable_scripts[selected_script_index].name

        api_param.script_args = []
        for sid, script in enumerate(p.scripts.scripts):
            # escape sagemaker plugin
            if script.title() == self.title():
                continue

            all_used_models = []
            script_args = p.script_args[script.args_from:script.args_to]
            if script.alwayson:
                logger.debug(f'{script.title().lower()} {script.args_from} {script.args_to}')
                api_param.alwayson_scripts[script.title().lower()] = {}
                api_param.alwayson_scripts[script.title().lower()]['args'] = []
                for _id, arg in enumerate(script_args):
                    parsed_args, used_models = process_args_by_plugin(api_param, script.title().lower(), arg, _id, script_args, args[-1], self.is_txt2img)
                    all_used_models.append(used_models)
                    api_param.alwayson_scripts[script.title().lower()]['args'].append(parsed_args)
            elif selected_script_name == script.name:
                api_param.script_name = script.name
                for _id, arg in enumerate(script_args):
                    parsed_args, used_models = process_args_by_plugin(api_param, script.name, arg, _id, script_args, args[-1], self.is_txt2img)
                    all_used_models.append(used_models)
                    api_param.script_args.append(parsed_args)

            if all_used_models:
                for used_models in all_used_models:
                    for key, vals in used_models.items():
                        if key not in models:
                            models[key] = []
                        for val in vals:
                            if val not in models[key] and val != None_Option_For_On_Cloud_Model:
                                models[key].append(val)

        # we not support automatic for simplicity because the default is Automatic
        # if user need, has to select a vae model manually in the setting page
        models['VAE'] = [args[2]]

        from modules.processing import get_fixed_seed

        seed = get_fixed_seed(p.seed)
        subseed = get_fixed_seed(p.subseed)
        p.setup_prompts()

        if type(seed) == list:
            p.all_seeds = seed
        else:
            p.all_seeds = [int(seed) + (x if p.subseed_strength == 0 else 0) for x in range(len(p.all_prompts))]

        if type(subseed) == list:
            p.all_subseeds = subseed
        else:
            p.all_subseeds = [int(subseed) + x for x in range(len(p.all_prompts))]

        p.init(p.all_prompts, p.all_seeds, p.all_subseeds)
        p.prompts = p.all_prompts
        p.negative_prompts = p.all_negative_prompts
        p.seeds = p.all_seeds
        p.subseeds = p.all_subseeds
        _prompts, extra_network_data = extra_networks.parse_prompts(p.all_prompts)

        # load lora
        for key, vals in extra_network_data.items():
            if key == 'lora':
                if not args[-1] or not args[-1]['lora']:
                    logger.error("please upload lora models!!!!")
                    continue
                for val in vals:
                    if 'Lora' not in models:
                        models['Lora'] = []
                    lora_filename = val.positional[0]
                    for filename in args[-1]['lora']:
                        if filename.startswith(lora_filename):
                            if lora_filename not in models['Lora']:
                                models['Lora'].append(filename)
                    if len(models['Lora']) == 0:
                        logger.error("please upload matched lora models!!!!")
            if key == 'hypernet':
                if not args[-1] or not args[-1]['hypernet']:
                    logger.error("please upload hypernetworks models!!!!")
                    continue
                for val in vals:
                    if 'hypernetworks' not in models:
                        models['hypernetworks'] = []
                    hypernet_filename = val.positional[0]
                    for filename in args[-1]['hypernet']:
                        if filename.startswith(hypernet_filename):
                            if hypernet_filename not in models['hypernetworks']:
                                models['hypernetworks'].append(filename)
                    if len(models['hypernetworks']) == 0:
                        logger.error("please upload matched hypernetworks models!!!!")

        if os.path.exists(cmd_opts.embeddings_dir) and not p.do_not_reload_embeddings:
            model_hijack.embedding_db.load_textual_inversion_embeddings()

        p.setup_conds()

        models['embeddings'] = sagemaker_ui.load_embeddings_list(p.user, p.user)

        err = None
        try:
            if sd_model_on_cloud == None_Option_For_On_Cloud_Model and always_on_cloud:
                raise Exception('Cloud Plugin is still loading and not ready to use, please wait and retry later.')

            from modules import call_queue
            call_queue.queue_lock.release()
            # logger.debug(f"########################{api_param}")
            inference_id_or_data = self.infer_manager.run(p.user, models, api_param, self.is_txt2img, endpoint_type)
            self.current_inference_id = inference_id_or_data
            self.inference_queue.put(inference_id_or_data)
        except Exception as e:
            logger.error(e)
            err = str(e)

        def process_image_inner_hijack(processing_param):
            if not self.default_images_inner:
                default_processing = importlib.import_module("modules.processing")
                self.default_images_inner = default_processing.process_images_inner

            if self.default_images_inner:
                processing.process_images_inner = self.default_images_inner

            if err:
                return Processed(
                    p,
                    images_list=[],
                    seed=0,
                    info=f"Inference job is failed: {', '.join(err) if isinstance(err, list) else err}",
                    subseed=0,
                    index_of_first_image=0,
                    infotexts=[],
                )

            image_list, info_text, plaintext_to_html, infotexts = sagemaker_ui.process_result_by_inference_id(
                inference_id_or_data, endpoint_type)

            processed = Processed(
                p,
                images_list=image_list,
                seed=p.all_seeds[0],
                info=infotexts,
                subseed=p.all_subseeds[0],
                index_of_first_image=0,
                infotexts=infotexts,
            )

            return processed

        default_processing = importlib.import_module("modules.processing")
        self.default_images_inner = default_processing.process_images_inner
        processing.process_images_inner = process_image_inner_hijack

    def process(self, p, *args):
        pass


script_callbacks.on_after_component(on_after_component_callback)
script_callbacks.on_ui_tabs(on_ui_tabs)

from aws_extension.auth_service.simple_cloud_auth import cloud_auth_manager

if cloud_auth_manager.enableAuth:
    cmd_opts.gradio_auth = cloud_auth_manager.create_config()


def fetch_user_data():
    while True:
        try:
            cloud_auth_manager.update_gradio_auth()
        except Exception as e:
            logger.error(e)
        time.sleep(30)


thread = threading.Thread(target=fetch_user_data)
thread.daemon = True
thread.start()

if os.environ.get('ON_DOCKER', "false") != "true":
    from modules import call_queue, fifo_lock

    class ImprovedFiFoLock(fifo_lock.FIFOLock):

        def release(self):
            if not self._inner_lock.locked() and not self._lock.locked():
                return

            fifo_lock.FIFOLock.release(self)


    call_queue.queue_lock = ImprovedFiFoLock()
