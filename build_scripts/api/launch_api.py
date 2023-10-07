from __future__ import annotations
import re
import os
import sys

from modules import timer
from modules import sd_models, extensions

timer.startup_timer.record("start")

# Whether to default to printing command output
default_command_live = (os.environ.get('WEBUI_LAUNCH_LIVE_OUTPUT') == "1")

if 'GRADIO_ANALYTICS_ENABLED' not in os.environ:
    os.environ['GRADIO_ANALYTICS_ENABLED'] = 'False'

import signal
import warnings
from typing import Iterable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from packaging import version

import logging

# We can't use cmd_opts for this because it will not have been initialized at this point.
log_level = os.environ.get("SD_WEBUI_LOG_LEVEL")
if log_level:
    log_level = getattr(logging, log_level.upper(), None) or logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

logging.getLogger("torch.distributed.nn").setLevel(logging.ERROR)  # sshh...
logging.getLogger("xformers").addFilter(lambda record: 'A matching Triton is not available' not in record.getMessage())

from modules import timer
startup_timer = timer.startup_timer
startup_timer.record("launcher")

import torch
# import pytorch_lightning   # noqa: F401 # pytorch_lightning should be imported after torch, but it re-enables warnings on import so import once to disable them
# warnings.filterwarnings(action="ignore", category=DeprecationWarning, module="pytorch_lightning")
warnings.filterwarnings(action="ignore", category=UserWarning, module="torchvision")
startup_timer.record("import torch")

# import gradio  # noqa: F401
startup_timer.record("import gradio")

from modules import  timer # noqa: F401
startup_timer.record("setup paths")

# import ldm.modules.encoders.modules  # noqa: F401
startup_timer.record("import ldm")

# from modules import extra_networks
# from modules.call_queue import wrap_gradio_gpu_call, wrap_queued_call, queue_lock  # noqa: F401

# Truncate version number of nightly/local build of PyTorch to not cause exceptions with CodeFormer or Safetensors
if ".dev" in torch.__version__ or "+git" in torch.__version__:
    torch.__long_version__ = torch.__version__
    torch.__version__ = re.search(r'[\d.]+[\d]', torch.__version__).group(0)

# from modules import shared, sd_samplers, upscaler, extensions, localization, ui_tempdir, ui_extra_networks, config_states
# import modules.codeformer_model as codeformer
# import modules.face_restoration
# import modules.gfpgan_model as gfpgan
# import modules.img2img

# import modules.lowvram
import modules.scripts
# import modules.sd_hijack
# import modules.sd_hijack_optimizations
# import modules.sd_models
# import modules.sd_vae
# import modules.sd_unet
# import modules.txt2img
# import modules.script_callbacks
# import modules.textual_inversion.textual_inversion
# import modules.progress

# import modules.hypernetworks.hypernetwork

startup_timer.record("other imports")

from modules import cmd_args

if os.environ.get('IGNORE_CMD_ARGS_ERRORS', None) is None:
    cmd_opts = cmd_args.parser.parse_args()
else:
    cmd_opts, _ = cmd_args.parser.parse_known_args()

if cmd_opts.server_name:
    server_name = cmd_opts.server_name
else:
    server_name = "0.0.0.0" if cmd_opts.listen else None

def fix_asyncio_event_loop_policy():
    """
        The default `asyncio` event loop policy only automatically creates
        event loops in the main threads. Other threads must create event
        loops explicitly or `asyncio.get_event_loop` (and therefore
        `.IOLoop.current`) will fail. Installing this policy allows event
        loops to be created automatically on any thread, matching the
        behavior of Tornado versions prior to 5.0 (or 5.0 on Python 2).
    """

    import asyncio

    if sys.platform == "win32" and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        # "Any thread" and "selector" should be orthogonal, but there's not a clean
        # interface for composing policies so pick the right base.
        _BasePolicy = asyncio.WindowsSelectorEventLoopPolicy  # type: ignore
    else:
        _BasePolicy = asyncio.DefaultEventLoopPolicy

    class AnyThreadEventLoopPolicy(_BasePolicy):  # type: ignore
        """Event loop policy that allows loop creation on any thread.
        Usage::

            asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
        """

        def get_event_loop(self) -> asyncio.AbstractEventLoop:
            try:
                return super().get_event_loop()
            except (RuntimeError, AssertionError):
                # This was an AssertionError in python 3.4.2 (which ships with debian jessie)
                # and changed to a RuntimeError in 3.4.3.
                # "There is no current event loop in thread %r"
                loop = self.new_event_loop()
                self.set_event_loop(loop)
                return loop

    asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())


def check_versions():
    # if shared.cmd_opts.skip_version_check:
    #     return

    expected_torch_version = "2.0.0"

    if version.parse(torch.__version__) < version.parse(expected_torch_version):
        print(f"""
You are running torch {torch.__version__}.
The program is tested to work with torch {expected_torch_version}.
To reinstall the desired version, run with commandline flag --reinstall-torch.
Beware that this will cause a lot of large files to be downloaded, as well as
there are reports of issues with training tab on the latest version.

Use --skip-version-check commandline argument to disable this check.
        """.strip())

    expected_xformers_version = "0.0.20"
    check_xformers = True
    if check_xformers:
        import xformers

        if version.parse(xformers.__version__) < version.parse(expected_xformers_version):
            print(f"""
You are running xformers {xformers.__version__}.
The program is tested to work with xformers {expected_xformers_version}.
To reinstall the desired version, run with commandline flag --reinstall-xformers.

Use --skip-version-check commandline argument to disable this check.
            """.strip())


# def restore_config_state_file():
#     config_state_file = shared.opts.restore_config_state_file
#     if config_state_file == "":
#         return

#     shared.opts.restore_config_state_file = ""
#     shared.opts.save(shared.config_filename)

#     if os.path.isfile(config_state_file):
#         print(f"*** About to restore extension state from file: {config_state_file}")
#         with open(config_state_file, "r", encoding="utf-8") as f:
#             config_state = json.load(f)
#             config_states.restore_extension_config(config_state)
#         startup_timer.record("restore extension config")
#     elif config_state_file:
#         print(f"!!! Config state backup not found: {config_state_file}")


def validate_tls_options():
    if not (cmd_opts.tls_keyfile and cmd_opts.tls_certfile):
        return

    try:
        if not os.path.exists(cmd_opts.tls_keyfile):
            print("Invalid path to TLS keyfile given")
        if not os.path.exists(cmd_opts.tls_certfile):
            print(f"Invalid path to TLS certfile: '{cmd_opts.tls_certfile}'")
    except TypeError:
        cmd_opts.tls_keyfile = cmd_opts.tls_certfile = None
        print("TLS setup invalid, running webui without TLS")
    else:
        print("Running with TLS")
    startup_timer.record("TLS")


def get_gradio_auth_creds() -> Iterable[tuple[str, ...]]:
    """
    Convert the gradio_auth and gradio_auth_path commandline arguments into
    an iterable of (username, password) tuples.
    """
    def process_credential_line(s) -> tuple[str, ...] | None:
        s = s.strip()
        if not s:
            return None
        return tuple(s.split(':', 1))

    if cmd_opts.gradio_auth:
        for cred in cmd_opts.gradio_auth.split(','):
            cred = process_credential_line(cred)
            if cred:
                yield cred

    if cmd_opts.gradio_auth_path:
        with open(cmd_opts.gradio_auth_path, 'r', encoding="utf8") as file:
            for line in file.readlines():
                for cred in line.strip().split(','):
                    cred = process_credential_line(cred)
                    if cred:
                        yield cred


def configure_sigint_handler():
    # make the program just exit at ctrl+c without waiting for anything
    def sigint_handler(sig, frame):
        print(f'Interrupted with signal {sig} in {frame}')
        os._exit(0)

    if not os.environ.get("COVERAGE_RUN"):
        # Don't install the immediate-quit handler when running under coverage,
        # as then the coverage report won't be generated.
        signal.signal(signal.SIGINT, sigint_handler)


# def configure_opts_onchange():
#     shared.opts.onchange("sd_model_checkpoint", wrap_queued_call(lambda: modules.sd_models.reload_model_weights()), call=False)
#     shared.opts.onchange("sd_vae", wrap_queued_call(lambda: modules.sd_vae.reload_vae_weights()), call=False)
#     shared.opts.onchange("sd_vae_as_default", wrap_queued_call(lambda: modules.sd_vae.reload_vae_weights()), call=False)
#     shared.opts.onchange("temp_dir", ui_tempdir.on_tmpdir_changed)
#     shared.opts.onchange("gradio_theme", shared.reload_gradio_theme)
#     shared.opts.onchange("cross_attention_optimization", wrap_queued_call(lambda: modules.sd_hijack.model_hijack.redo_hijack(shared.sd_model)), call=False)
#     startup_timer.record("opts onchange")


def initialize():
    # TODO: do we need keep this for api? Xiujuan
    fix_asyncio_event_loop_policy()
    # TODO: do we need keep this for api? Xiujuan
    validate_tls_options()
    # TODO: do we need keep this for api? Xiujuan
    configure_sigint_handler()
    check_versions()

    extensions.list_extensions()
    startup_timer.record("list extensions")
    
    # # TODO: do we need cleanup_models? YX
    # modelloader.cleanup_models()
    # # TODO: do we need opt_onchange? YX
    # configure_opts_onchange()

    # # TODO: do we need setup_model? YX
    # modules.sd_models.setup_model()
    # startup_timer.record("setup SD model")

    # # TODO: do we need setup_model for codeformer? YX
    # codeformer.setup_model(cmd_opts.codeformer_models_path)
    # startup_timer.record("setup codeformer")

    # # TODO: do we need setup_model for gfpgan? YX
    # gfpgan.setup_model(cmd_opts.gfpgan_models_path)
    # startup_timer.record("setup gfpgan")

    # initialize_rest(reload_script_modules=False)
    sd_models.list_models()

    # TODO: do we need load scripts? YX
    with startup_timer.subcategory("load scripts"):
        modules.scripts.load_scripts()

    def load_model():
         """
         Accesses shared.sd_model property to load model.
         After it's available, if it has been loaded before this access by some extension,
         its optimization may be None because the list of optimizaers has neet been filled
         by that time, so we apply optimization again.
         """

         from modules import shared
         # shared.sd_model  # noqa: B018

         # if modules.sd_hijack.current_optimizer is None:
         #     modules.sd_hijack.apply_optimizations()

         # # TODO: disable to debug pipeline
         ### load pipeline
         shared.sd_pipeline

    from threading import Thread
    Thread(target=load_model).start()


# def initialize_rest(*, reload_script_modules=False):
    """
    Called both from initialize() and when reloading the webui.
    """
    # # TODO: do we need set samplers? YX
    # sd_samplers.set_samplers()
    # extensions.list_extensions()
    # startup_timer.record("list extensions")

    # restore_config_state_file()

    # if cmd_opts.ui_debug_mode:
    #     shared.sd_upscalers = upscaler.UpscalerLanczos().scalers
    #     modules.scripts.load_scripts()
    #     return

    # # TODO: do we need list models? YX
    # modules.sd_models.list_models()
    # startup_timer.record("list SD models")

    # # TODO: do we need list localizations? YX
    # localization.list_localizations(cmd_opts.localizations_dir)

    # # TODO: do we need load scripts? YX
    # with startup_timer.subcategory("load scripts"):
    #     modules.scripts.load_scripts()

    # if reload_script_modules:
    #     for module in [module for name, module in sys.modules.items() if name.startswith("modules.ui")]:
    #         importlib.reload(module)
    #     startup_timer.record("reload script modules")

    # # TODO: do we need load_upscalers? YX
    # modelloader.load_upscalers()
    # startup_timer.record("load upscalers")

    # # TODO: do we need refresh models? YX
    # modules.sd_vae.refresh_vae_list()
    # startup_timer.record("refresh VAE")
    # modules.textual_inversion.textual_inversion.list_textual_inversion_templates()
    # startup_timer.record("refresh textual inversion templates")

    # TODO: do we need list optimizers? YX
    # modules.script_callbacks.on_list_optimizers(modules.sd_hijack_optimizations.list_optimizers)
    # modules.sd_hijack.list_optimizers()
    # startup_timer.record("scripts list_optimizers")

    # # TODO: do we need list unets? YX
    # modules.sd_unet.list_unets()
    # startup_timer.record("scripts list_unets")

    # def load_model():
    #     """
    #     Accesses shared.sd_model property to load model.
    #     After it's available, if it has been loaded before this access by some extension,
    #     its optimization may be None because the list of optimizaers has neet been filled
    #     by that time, so we apply optimization again.
    #     """

    #     shared.sd_model  # noqa: B018

    #     if modules.sd_hijack.current_optimizer is None:
    #         modules.sd_hijack.apply_optimizations()

    # # TODO: do we need load_models or first_time_calculation? YX
    # Thread(target=load_model).start()

    # Thread(target=devices.first_time_calculation).start()

    # shared.reload_hypernetworks()
    # startup_timer.record("reload hypernetworks")

    # ui_extra_networks.initialize()
    # ui_extra_networks.register_default_pages()

    # extra_networks.initialize()
    # extra_networks.register_default_extra_networks()
    # startup_timer.record("initialize extra networks")


def setup_middleware(app):
    app.middleware_stack = None  # reset current middleware to allow modifying user provided list
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    configure_cors_middleware(app)
    app.build_middleware_stack()  # rebuild middleware stack on-the-fly


def configure_cors_middleware(app):
    cors_options = {
        "allow_methods": ["*"],
        "allow_headers": ["*"],
        "allow_credentials": True,
    }
    if cmd_opts.cors_allow_origins:
        cors_options["allow_origins"] = cmd_opts.cors_allow_origins.split(',')
    if cmd_opts.cors_allow_origins_regex:
        cors_options["allow_origin_regex"] = cmd_opts.cors_allow_origins_regex
    app.add_middleware(CORSMiddleware, **cors_options)


from modules.call_queue import queue_lock  # noqa: F401

def create_api(app):
    from modules.api.api import Api
    api = Api(app, queue_lock)
    return api


def main_api():
    initialize()

    app = FastAPI()
    setup_middleware(app)
    api = create_api(app)

    # modules.script_callbacks.app_started_callback(None, app)

    print(f"Startup time: {startup_timer.summary()}.")
    api.launch(
        server_name="0.0.0.0" if cmd_opts.listen else "127.0.0.1",
        port=cmd_opts.port if cmd_opts.port else 7861
    )

if __name__ == "__main__":
    main_api()
