from queue import Queue
import importlib
import logging
import gradio as gr
import os

import utils
from aws_extension.cloud_infer_service.simple_sagemaker_infer import SimpleSagemakerInfer
import modules.scripts as scripts
from aws_extension.sagemaker_ui import None_Option_For_On_Cloud_Model, load_model_list, load_controlnet_list
from dreambooth_on_cloud.ui import ui_tabs_callback
from modules import script_callbacks, sd_models, processing, extra_networks, shared
from modules.api.models import StableDiffusionTxt2ImgProcessingAPI, StableDiffusionImg2ImgProcessingAPI
from modules.sd_hijack import model_hijack
from modules.processing import Processed
from modules.shared import cmd_opts, opts
from aws_extension import sagemaker_ui

from aws_extension.cloud_models_manager.sd_manager import CloudSDModelsManager, postfix
from aws_extension.inference_scripts_helper.scripts_processor import process_args_by_plugin
from aws_extension.sagemaker_ui_tab import on_ui_tabs
from aws_extension.sagemaker_ui_utils import on_after_component_callback
from modules.ui_components import ToolButton

dreambooth_available = True
logger = logging.getLogger(__name__)
logger.setLevel(utils.LOGGING_LEVEL)


def dummy_function(*args, **kwargs):
    return []


try:
    from dreambooth_on_cloud.train import (
        async_cloud_train,
        get_cloud_db_model_name_list,
        wrap_load_model_params,
        get_train_job_list,
        get_sorted_cloud_dataset
    )
    from dreambooth_on_cloud.create_model import (
        get_sd_cloud_models,
        get_create_model_job_list,
        cloud_create_model,
    )
except Exception as e:
    logging.warning(
        "[main]dreambooth_on_cloud is not installed or can not be imported, using dummy function to proceed.")
    dreambooth_available = False
    cloud_train = dummy_function
    get_cloud_db_model_name_list = dummy_function
    wrap_load_model_params = dummy_function
    get_train_job_list = dummy_function
    get_sorted_cloud_dataset = dummy_function
    get_sd_cloud_models = dummy_function
    get_create_model_job_list = dummy_function
    cloud_create_model = dummy_function


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

    ph = None

    txt2img_controlnet_dropdown_batch = {}
    img2img_controlnet_dropdown_batch = {}
    txt2img_controlnet_refresh_btn_batch = {}
    img2img_controlnet_refresh_btn_batch = {}

    def title(self):
        return "SageMaker embeddings"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def after_component(self, component, **kwargs):
        # controlnet models count
        max_models = shared.opts.data.get("control_net_unit_count", 10)
        if type(component) is gr.Button:
            if self.is_txt2img and getattr(component, 'elem_id', None) == f'txt2img_generate':
                self.txt2img_generate_btn = component
            elif self.is_img2img and getattr(component, 'elem_id', None) == f'img2img_generate':
                self.img2img_generate_btn = component

        if type(component) is gr.Dropdown:
            elem_id = ('txt2img_' if self.is_txt2img else 'img2img_') + 'checkpoint'
            component_elem_id = getattr(component, 'elem_id', '')
            elem_id_tabname = ("img2img" if self.is_img2img else "txt2img") + "_controlnet"
            if component_elem_id == elem_id:
                if self.is_txt2img:
                    self.txt2img_refiner_ckpt_dropdown = component
                if self.is_img2img:
                    self.img2img_refiner_ckpt_dropdown = component
            elif self.is_txt2img and component_elem_id and component_elem_id.endswith("_controlnet_model_dropdown"):
                if max_models > 1:
                    for i in range(max_models):
                        tabname = f"ControlNet-{i}"
                        elem_id_controlnet = f"{elem_id_tabname}_{tabname}_controlnet_model_dropdown"
                        if component_elem_id == elem_id_controlnet:
                            self.txt2img_controlnet_dropdown_batch[i] = component
                            break
                else:
                    tabname = "ControlNet"
                    elem_id_controlnet = f"{elem_id_tabname}_{tabname}_controlnet_model_dropdown"
                    if component_elem_id == elem_id_controlnet:
                        self.txt2img_controlnet_dropdown_batch[0] = component
            elif self.is_img2img and component_elem_id and component_elem_id.endswith("_controlnet_model_dropdown"):
                if max_models > 1:
                    for i in range(max_models):
                        tabname = f"ControlNet-{i}"
                        elem_id_controlnet = f'{elem_id_tabname}_{tabname}_controlnet_model_dropdown'
                        if component_elem_id == elem_id_controlnet:
                            self.img2img_controlnet_dropdown_batch[i] = component
                            break
                else:
                    tabname = "ControlNet"
                    elem_id_controlnet = f"{elem_id_tabname}_{tabname}_controlnet_model_dropdown"
                    if component_elem_id == elem_id_controlnet:
                        self.img2img_controlnet_dropdown_batch[0] = component

        if type(component) is ToolButton:
            elem_id = ('txt2img_' if self.is_txt2img else 'img2img_') + 'checkpoint_refresh'
            component_elem_id = getattr(component, 'elem_id', '')
            if component_elem_id == elem_id:
                if self.is_txt2img:
                    self.txt2img_refiner_ckpt_refresh_btn = component
                if self.is_img2img:
                    self.img2img_refiner_ckpt_refresh_btn = component

        # controlnet refresh button type is not webui ToolButton, maybe there is no controlnet, so use str not class
        if str(type(component)) == "<class 'scripts.controlnet_ui.tool_button.ToolButton'>":
            component_elem_id = getattr(component, 'elem_id', '')
            elem_id_tabname = ("img2img" if self.is_img2img else "txt2img") + "_controlnet"
            if self.is_txt2img and component_elem_id and component_elem_id.endswith('_controlnet_refresh_models'):
                logger.debug(f" is_txt2img_controlnet_model_refresh {type(component)}")
                if max_models > 1:
                    for i in range(max_models):
                        tabname = f"ControlNet-{i}"
                        elem_id_controlnet = f"{elem_id_tabname}_{tabname}_controlnet_refresh_models"
                        if component_elem_id == elem_id_controlnet:
                            self.txt2img_controlnet_refresh_btn_batch[i] = component
                            break
                else:
                    tabname = "ControlNet"
                    elem_id_controlnet = f"{elem_id_tabname}_{tabname}_controlnet_refresh_models"
                    if component_elem_id == elem_id_controlnet:
                        self.txt2img_controlnet_dropdown_batch[0] = component
            elif self.is_img2img and component_elem_id and component_elem_id.endswith('_controlnet_refresh_models'):
                logger.debug(f" is_img2img_controlnet_model_refresh {type(component)}")
                if max_models > 1:
                    for i in range(max_models):
                        tabname = f"ControlNet-{i}"
                        elem_id_controlnet = f"{elem_id_tabname}_{tabname}_controlnet_refresh_models"
                        if component_elem_id == elem_id_controlnet:
                            self.img2img_controlnet_refresh_btn_batch[i] = component
                            break
                else:
                    tabname = "ControlNet"
                    elem_id_controlnet = f"{elem_id_tabname}_{tabname}_controlnet_refresh_models"
                    if component_elem_id == elem_id_controlnet:
                        self.img2img_controlnet_dropdown_batch[0] = component

        async def _update_result():
            if self.inference_queue and not self.inference_queue.empty():
                inference_id = self.inference_queue.get()
                self.latest_result = sagemaker_ui.process_result_by_inference_id(inference_id)
                return self.latest_result

            return gr.skip(), gr.skip(), gr.skip()

        if self.txt2img_html_info and self.txt2img_gallery and self.txt2img_generation_info:
            self.txt2img_generation_info.change(
                fn=lambda: sagemaker_ui.async_loop_wrapper(_update_result),
                inputs=None,
                outputs=[self.txt2img_gallery, self.txt2img_generation_info, self.txt2img_html_info]
            )

        if type(component) is gr.Textbox and getattr(component, 'elem_id',
                                                     None) == 'generation_info_img2img' and self.is_img2img:
            self.img2img_generation_info = component

        if type(component) is gr.Gallery and getattr(component, 'elem_id',
                                                     None) == 'img2img_gallery' and self.is_img2img:
            self.img2img_gallery = component

        if type(component) is gr.HTML and getattr(component, 'elem_id',
                                                  None) == 'html_info_img2img' and self.is_img2img:
            self.img2img_html_info = component

        if self.img2img_html_info and self.img2img_gallery and self.img2img_generation_info:
            self.img2img_generation_info.change(
                fn=lambda: sagemaker_ui.async_loop_wrapper(_update_result),
                inputs=None,
                outputs=[self.img2img_gallery, self.img2img_generation_info, self.img2img_html_info]
            )
        pass

    def ui(self, is_img2img):
        def _check_generate(model_selected, pr: gr.Request):
            on_cloud = model_selected and model_selected != None_Option_For_On_Cloud_Model
            result = [f'Generate{" on Cloud" if on_cloud else ""}', gr.update(visible=not on_cloud)]
            if not on_cloud:
                result.append(gr.update(choices=sd_models.checkpoint_tiles()))
            else:
                result.append(gr.update(choices=load_model_list(pr.username, pr.username)))
            result.append(sagemaker_ui.load_lora_models(pr.username, pr.username))
            max_models = shared.opts.data.get("control_net_unit_count", 10)
            if max_models > 0:
                for i in range(max_models):
                    result.append(gr.update(choices=load_controlnet_list(pr.username, pr.username)))
            # sync append fresh button
            if max_models > 0:
                for i in range(max_models):
                    result.append(gr.update(visible=not on_cloud))
            return result

        if not is_img2img:
            model_on_cloud, sd_vae_on_cloud_dropdown, inference_job_dropdown, primary_model_name, \
                secondary_model_name, tertiary_model_name, \
                modelmerger_merge_on_cloud, lora_model_state = sagemaker_ui.create_ui(is_img2img)
            outputs = [self.txt2img_generate_btn, self.txt2img_refiner_ckpt_refresh_btn,
                       self.txt2img_refiner_ckpt_dropdown, lora_model_state]
            for value in self.txt2img_controlnet_dropdown_batch.values():
                outputs.append(value)
            for value in self.txt2img_controlnet_refresh_btn_batch.values():
                outputs.append(value)
            model_on_cloud.change(_check_generate, inputs=model_on_cloud,
                                  outputs=outputs)

            return [model_on_cloud, sd_vae_on_cloud_dropdown, inference_job_dropdown,
                    primary_model_name, secondary_model_name, tertiary_model_name, modelmerger_merge_on_cloud, lora_model_state]
        else:
            model_on_cloud, sd_vae_on_cloud_dropdown, inference_job_dropdown, primary_model_name, \
            secondary_model_name, tertiary_model_name, \
                modelmerger_merge_on_cloud, lora_model_state = sagemaker_ui.create_ui(is_img2img)
            outputs = [self.img2img_generate_btn, self.img2img_refiner_ckpt_refresh_btn,
                       self.img2img_refiner_ckpt_dropdown, lora_model_state]
            for value in self.img2img_controlnet_dropdown_batch.values():
                outputs.append(value)
            for value in self.img2img_controlnet_refresh_btn_batch.values():
                outputs.append(value)
            model_on_cloud.change(_check_generate, inputs=model_on_cloud,
                                  outputs=outputs)
            return [model_on_cloud, sd_vae_on_cloud_dropdown, inference_job_dropdown,
                    primary_model_name, secondary_model_name, tertiary_model_name, modelmerger_merge_on_cloud, lora_model_state]

    def before_process(self, p, *args):
        on_docker = os.environ.get('ON_DOCKER', "false")
        if on_docker == "true":
            return

        # check if endpoint is inService
        sd_model_on_cloud = args[0]
        if sd_model_on_cloud == None_Option_For_On_Cloud_Model:
            return

        current_model = sd_models.select_checkpoint()
        logger.debug(current_model.name)
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
                logger.debug(f'{script.name} {script.args_from} {script.args_to}')
                api_param.alwayson_scripts[script.name] = {}
                api_param.alwayson_scripts[script.name]['args'] = []
                for _id, arg in enumerate(script_args):
                    parsed_args, used_models = process_args_by_plugin(api_param, script.name, arg, _id, script_args)
                    all_used_models.append(used_models)
                    api_param.alwayson_scripts[script.name]['args'].append(parsed_args)
            elif selected_script_name == script.name:
                api_param.script_name = script.name
                for _id, arg in enumerate(script_args):
                    parsed_args, used_models = process_args_by_plugin(api_param, script.name, arg, _id, script_args)
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


        # fixme: not handle batches yet
        # we not support automatic for simplicity because the default is Automatic
        # if user need, has to select a vae model manually in the setting page
        if 'sd_vae' in opts.quicksettings_list:
            models['VAE'] = [args[1]]

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
                for val in vals:
                    if 'Lora' not in models:
                        models['Lora'] = []

                    lora_filename = val.positional[0]
                    for filename in args[-1]:
                        if filename.startswith(lora_filename):
                            if lora_filename not in models['Lora']:
                                models['Lora'].append(filename)
            if key == 'hypernet':
                logger.debug(key, vals)
                for val in vals:
                    if 'hypernetworks' not in models:
                        models['hypernetworks'] = []

                    hypernet_filename = shared.hypernetworks[val.positional[0]].split(os.path.sep)[-1]
                    if hypernet_filename not in models['hypernetworks']:
                        models['hypernetworks'].append(hypernet_filename)

        if os.path.exists(cmd_opts.embeddings_dir) and not p.do_not_reload_embeddings:
            model_hijack.embedding_db.load_textual_inversion_embeddings()

        p.setup_conds()

        # load all embedding models
        models['embeddings'] = [val.filename.split(os.path.sep)[-1] for val in
                                model_hijack.embedding_db.word_embeddings.values()]

        err = None
        try:
            from modules import call_queue
            call_queue.queue_lock.release()
            logger.debug(f"########################{api_param}")
            inference_id = self.infer_manager.run(p.user, models, api_param, self.is_txt2img)
            self.current_inference_id = inference_id
            self.inference_queue.put(inference_id)
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
                    info=f"Inference job is failed: { ', '.join(err) if isinstance(err, list) else err}",
                    subseed=0,
                    index_of_first_image=0,
                    infotexts=[],
                )

            image_list, info_text, plaintext_to_html, infotexts = sagemaker_ui.process_result_by_inference_id(inference_id)

            # yield Processed(
            #     p,
            #     images_list=image_list,
            #     seed=0,
            #     # info=f'Inference job with id {inference_id} has created and running on cloud now. Use Inference job in the SageMaker part to see the result.',
            #     info=info_text,
            #     subseed=0,
            #     index_of_first_image=0,
            #     infotexts=info_text,
            # )

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
script_callbacks.ui_tabs_callback = ui_tabs_callback

from aws_extension.auth_service.simple_cloud_auth import cloud_auth_manager

if cloud_auth_manager.enableAuth:
    cmd_opts.gradio_auth = cloud_auth_manager.create_config()

if os.environ.get('ON_DOCKER', "false") != "true":
    from modules import call_queue, fifo_lock

    class ImprovedFiFoLock(fifo_lock.FIFOLock):

        def release(self):
            if not self._inner_lock.locked() and not self._lock.locked():
                return

            fifo_lock.FIFOLock.release(self)


    call_queue.queue_lock = ImprovedFiFoLock()
