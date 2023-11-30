import collections
import os.path
import sys
#import gc
import threading

import torch
# import re
# import safetensors.torch
# from omegaconf import OmegaConf
# from os import mkdir
# from urllib import request
# import ldm.modules.midas as midas

# from ldm.util import instantiate_from_config

from modules import shared, modelloader, devices, sd_vae, errors, hashes
from modules.paths_internal import models_path
from modules.timer import Timer
import tomesd
from diffusers import StableDiffusionPipeline, StableDiffusionXLPipeline

model_dir = "Stable-diffusion"
model_path = os.path.abspath(os.path.join(models_path, model_dir))

checkpoints_list = {}
checkpoint_aliases = {}
checkpoint_alisases = checkpoint_aliases  # for compatibility with old name
checkpoints_loaded = collections.OrderedDict()


class CheckpointInfo:
    def __init__(self, filename):
        self.filename = filename
        abspath = os.path.abspath(filename)

        if shared.cmd_opts.ckpt_dir is not None and abspath.startswith(shared.cmd_opts.ckpt_dir):
            name = abspath.replace(shared.cmd_opts.ckpt_dir, '')
        elif abspath.startswith(model_path):
            name = abspath.replace(model_path, '')
        else:
            name = os.path.basename(filename)

        if name.startswith("\\") or name.startswith("/"):
            name = name[1:]

        self.name = name
        self.name_for_extra = os.path.splitext(os.path.basename(filename))[0]
        self.model_name = os.path.splitext(name.replace("/", "_").replace("\\", "_"))[0]
        self.hash = model_hash(filename)

        self.sha256 = hashes.sha256_from_cache(self.filename, f"checkpoint/{name}")
        self.shorthash = self.sha256[0:10] if self.sha256 else None

        self.title = name if self.shorthash is None else f'{name} [{self.shorthash}]'

        self.ids = [self.hash, self.model_name, self.title, name, f'{name} [{self.hash}]'] + ([self.shorthash, self.sha256, f'{self.name} [{self.shorthash}]'] if self.shorthash else [])

        # self.metadata = {}

        # _, ext = os.path.splitext(self.filename)
        # if ext.lower() == ".safetensors":
        #     try:
        #         self.metadata = read_metadata_from_safetensors(filename)
        #     except Exception as e:
        #         errors.display(e, f"reading checkpoint metadata: {filename}")

    def register(self):
        checkpoints_list[self.title] = self
        for id in self.ids:
            checkpoint_aliases[id] = self

    def calculate_shorthash(self):
        self.sha256 = hashes.sha256(self.filename, f"checkpoint/{self.name}")
        if self.sha256 is None:
            return

        self.shorthash = self.sha256[0:10]

        if self.shorthash not in self.ids:
            self.ids += [self.shorthash, self.sha256, f'{self.name} [{self.shorthash}]']

        checkpoints_list.pop(self.title)
        self.title = f'{self.name} [{self.shorthash}]'
        self.register()

        return self.shorthash




def list_models():
    checkpoints_list.clear()
    checkpoint_aliases.clear()

    cmd_ckpt = shared.cmd_opts.ckpt
    if shared.cmd_opts.no_download_sd_model or cmd_ckpt != shared.sd_model_file or os.path.exists(cmd_ckpt):
        model_url = None
    else:
        model_url = "https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors"

    model_list = modelloader.load_models(model_path=model_path, model_url=model_url, command_path=shared.cmd_opts.ckpt_dir, ext_filter=[".ckpt", ".safetensors"], download_name="v1-5-pruned-emaonly.safetensors", ext_blacklist=[".vae.ckpt", ".vae.safetensors"])

    if os.path.exists(cmd_ckpt):
        checkpoint_info = CheckpointInfo(cmd_ckpt)
        checkpoint_info.register()

        shared.opts.data['sd_model_checkpoint'] = checkpoint_info.title
    elif cmd_ckpt is not None and cmd_ckpt != shared.default_sd_model_file:
        print(f"Checkpoint in --ckpt argument not found (Possible it was moved to {model_path}: {cmd_ckpt}", file=sys.stderr)

    for filename in sorted(model_list, key=str.lower):
        checkpoint_info = CheckpointInfo(filename)
        checkpoint_info.register()


def get_closet_checkpoint_match(search_string):
    checkpoint_info = checkpoint_aliases.get(search_string, None)
    if checkpoint_info is not None:
        return checkpoint_info

    found = sorted([info for info in checkpoints_list.values() if search_string in info.title], key=lambda x: len(x.title))
    if found:
        return found[0]

    return None


def model_hash(filename):
    """old hash that only looks at a small part of the file and is prone to collisions"""

    try:
        with open(filename, "rb") as file:
            import hashlib
            m = hashlib.sha256()

            file.seek(0x100000)
            m.update(file.read(0x10000))
            return m.hexdigest()[0:8]
    except FileNotFoundError:
        return 'NOFILE'


def select_checkpoint():
    """Raises `FileNotFoundError` if no checkpoints are found."""
    model_checkpoint = shared.opts.sd_model_checkpoint

    checkpoint_info = checkpoint_aliases.get(model_checkpoint, None)
    if checkpoint_info is not None:
        return checkpoint_info

    if len(checkpoints_list) == 0:
        error_message = "No checkpoints found. When searching for checkpoints, looked at:"
        if shared.cmd_opts.ckpt is not None:
            error_message += f"\n - file {os.path.abspath(shared.cmd_opts.ckpt)}"
        error_message += f"\n - directory {model_path}"
        if shared.cmd_opts.ckpt_dir is not None:
            error_message += f"\n - directory {os.path.abspath(shared.cmd_opts.ckpt_dir)}"
        error_message += "Can't run without a checkpoint. Find and place a .ckpt or .safetensors file into any of those locations."
        raise FileNotFoundError(error_message)

    checkpoint_info = next(iter(checkpoints_list.values()))
    if model_checkpoint is not None:
        print(f"Checkpoint {model_checkpoint} not found; loading fallback {checkpoint_info.title}", file=sys.stderr)

    return checkpoint_info


def apply_token_merging(sd_model, token_merging_ratio):
    """
    Applies speed and memory optimizations from tomesd.
    """

    current_token_merging_ratio = getattr(sd_model, 'applied_token_merged_ratio', 0)

    if current_token_merging_ratio == token_merging_ratio:
        return

    if current_token_merging_ratio > 0:
        tomesd.remove_patch(sd_model)

    if token_merging_ratio > 0:
        tomesd.apply_patch(
            sd_model,
            ratio=token_merging_ratio,
            use_rand=False,  # can cause issues with some samplers
            merge_attn=True,
            merge_crossattn=False,
            merge_mlp=False
        )

    sd_model.applied_token_merged_ratio = token_merging_ratio


class DiffuserPipelineData:
    def __init__(self):
        self.sd_pipeline = None
        self.was_loaded_at_least_once = False
        self.lock = threading.Lock()

    def get_sd_pipeline(self):
        if self.was_loaded_at_least_once:
            return self.sd_pipeline

        if self.sd_pipeline is None:
            with self.lock:
                if self.sd_pipeline is not None or self.was_loaded_at_least_once:
                    return self.sd_pipeline

                try:
                    load_pipeline()
                except Exception as e:
                    errors.display(e, "loading diffuser pipeline", full_traceback=True)
                    print("", file=sys.stderr)
                    print("Diffuser pipeline failed to load", file=sys.stderr)
                    self.sd_pipeline = None

        return self.sd_pipeline

    def set_sd_pipeline(self, v):
        self.sd_pipeline = v

pipeline_data = DiffuserPipelineData()

def send_model_to_trash(m):
    m.to("meta")
    devices.torch_gc()


def load_pipeline(checkpoint_info=None):
    checkpoint_info = checkpoint_info or select_checkpoint()

    if pipeline_data.sd_pipeline:
        send_model_to_trash(pipeline_data.sd_pipeline)
        pipeline_data.sd_pipeline = None
        devices.torch_gc()


    timer = Timer()

    sd_model_hash = checkpoint_info.calculate_shorthash()
    timer.record("calculate hash")

    shared.opts.data["sd_model_checkpoint"] = checkpoint_info.title

    file_extension = checkpoint_info.filename.rsplit(".", 1)[-1]   
    from_safetensors = file_extension == "safetensors"
    if from_safetensors:
        from safetensors.torch import load_file as safe_load
        checkpoint = safe_load(checkpoint_info.filename, device="cpu")
    else:
        checkpoint = torch.load(checkpoint_info.filename, map_location="cpu")

    timer.record("recoginition model type to load different pipeline")
    
    key_name_sd_xl_base = "conditioner.embedders.1.model.transformer.resblocks.9.mlp.c_proj.bias"
    key_name_sd_xl_refiner = "conditioner.embedders.0.model.transformer.resblocks.9.mlp.c_proj.bias"

    pipeline_class = StableDiffusionPipeline
    if key_name_sd_xl_base in checkpoint or key_name_sd_xl_refiner in checkpoint:
        pipeline_class = StableDiffusionXLPipeline
    
    checkpoint = None
    
    #from diffusers import StableDiffusionInpaintPipeline
    #pipe_inpaint = StableDiffusionInpaintPipeline.from_single_file('/home/ubuntu/de_webui/stable-diffusion-aws-extension/build_scripts/api/models/Stable-diffusion/majicmixRealistic_v7.safetensors', torch_dtype=torch.float16, variant="fp16").to('cuda')


    pipeline_data.sd_pipeline = pipeline_class.from_single_file(checkpoint_info.filename, torch_dtype=torch.float16, load_safety_checker=False, variant="fp16")
    timer.record("load pipeline from single file")


    pipeline_data.sd_pipeline.enable_xformers_memory_efficient_attention()
    #pipeline_data.sd_pipeline.enable_sequential_cpu_offload()
    
    pipeline_name = str(type(pipeline_data.sd_pipeline)).split('.')[-1][:-2]


    pipeline_data.sd_pipeline.pipeline_name = pipeline_name
    shared.opts.data["sd_checkpoint_hash"] = checkpoint_info.sha256
    shared.opts.data["sd_model_hash"] = sd_model_hash
    shared.opts.data["sd_model_checkpoint_path"] = checkpoint_info.filename
    shared.opts.data["sd_checkpoint_info"] = checkpoint_info
    shared.opts.data["sd_checkpoint_name"] = checkpoint_info.model_name


    pipeline_data.sd_pipeline.to(shared.device)
    timer.record("move model to device")

    pipeline_data.was_loaded_at_least_once = True
    
    sd_vae.delete_base_vae()
    sd_vae.clear_loaded_vae()
    vae_file, vae_source = sd_vae.resolve_vae(checkpoint_info.filename)
    sd_vae.load_vae(pipeline_data.sd_pipeline, vae_file, vae_source)
    timer.record("load VAE")

    embeddings_dir = shared.cmd_opts.embeddings_dir
    try:
        embeddings = os.listdir(embeddings_dir)
        embeddings_path = []
        for embedding in embeddings:
            embeddings_path.append(os.path.join(embeddings_dir, embedding))
        pipeline_data.sd_pipeline.load_textual_inversion(embeddings_path)
    except:
        print(f"No embeddings.")
    
    timer.record("load textual inversion embeddings")

    print(f"Model loaded in {timer.summary()}.")


def reload_pipeline_weights(sd_pipeline=None, info=None):
    from modules import devices
    checkpoint_info = info or select_checkpoint()

    # if not sd_pipeline:
    #     sd_pipeline = pipeline_data.sd_pipeline

    if pipeline_data.sd_pipeline is None:  # previous model load failed
        current_checkpoint_info = None
    else:
        current_checkpoint_info = shared.opts.data["sd_checkpoint_info"] #sd_pipeline.sd_checkpoint_info
        if shared.opts.data["sd_model_checkpoint_path"] == checkpoint_info.filename:
           return

        pipeline_data.sd_pipeline.to(devices.cpu)
        send_model_to_trash(pipeline_data.sd_pipeline)

    timer = Timer()
    #del pipeline_data.sd_pipeline
    pipeline_data.sd_pipeline = None
    try:
        load_pipeline(checkpoint_info)
    except Exception:
        print("Failed to load checkpoint, restoring previous")
        load_pipeline(current_checkpoint_info)

    timer.record("move model to device")

    return pipeline_data.sd_pipeline
