import logging
import os
from datetime import datetime

from dotenv import load_dotenv

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

load_dotenv()

host_url = os.environ.get("API_GATEWAY_URL")
if not host_url:
    raise Exception("API_GATEWAY_URL is empty")

region_name = host_url.split('.')[2]
if not region_name:
    raise Exception("API_GATEWAY_URL is invalid")

# Remove "/prod" or "/prod/" from the end of the host_url
host_url = host_url.replace("/prod/", "")
host_url = host_url.replace("/prod", "")
if host_url.endswith("/"):
    host_url = host_url[:-1]
logger.info(f"config.host_url: {host_url}")

api_key = os.environ.get("API_GATEWAY_URL_TOKEN")
if not api_key:
    raise Exception("API_GATEWAY_URL_TOKEN is empty")
logger.info(f"config.api_key: {api_key}")

username = "api"
logger.info(f"config.username: {username}")

bucket = os.environ.get("API_BUCKET")
if not bucket:
    raise Exception("API_BUCKET is empty")
logger.info(f"config.bucket: {bucket}")

test_fast = os.environ.get("TEST_FAST") == "true"
logger.info(f"config.test_fast: {test_fast}")

is_gcr = region_name.startswith("cn-")
logger.info(f"config.is_gcr: {is_gcr}")

is_local = os.environ.get("SNS_ARN") is None
logger.info(f"config.is_local: {is_local}")

role_name = "role_name"
logger.info(f"config.role_name: {role_name}")

current_time = datetime.utcnow().strftime("%m%d%H%M%S")

endpoint_name = f"test-{current_time}"
logger.info(f"config.endpoint_name: {endpoint_name}")

dataset_name = "dataset_name"
logger.info(f"config.dataset_name: {dataset_name}")

train_model_name = "train_model_name"
logger.info(f"config.train_model_name: {train_model_name}")

train_wd14_model_name = "wd14_model_name"
logger.info(f"config.train_wd14_model_name: {train_wd14_model_name}")

model_name = "test-model"
logger.info(f"config.model_name: {model_name}")

async_instance_type = os.environ.get("ASYNC_INSTANCE_TYPE", "ml.g5.2xlarge")
if is_gcr:
    async_instance_type = "ml.g4dn.2xlarge"
logger.info(f"config.async_instance_type: {async_instance_type}")

real_time_instance_type = os.environ.get("REAL_TIME_INSTANCE_TYPE", "ml.g5.2xlarge")
if is_gcr:
    real_time_instance_type = "ml.g4dn.4xlarge"
logger.info(f"config.real_time_instance_type: {real_time_instance_type}")

initial_instance_count = "2"
if is_gcr:
    initial_instance_count = "1"
logger.info(f"config.initial_instance_count: {initial_instance_count}")

default_model_id = "v1-5-pruned-emaonly.safetensors"
logger.info(f"config.default_model_id: {default_model_id}")

ckpt_message = "placeholder for chkpts upload test"
logger.info(f"config.ckpt_message: {ckpt_message}")

train_instance_type = os.environ.get("TRAIN_INSTANCE_TYPE", "ml.g5.2xlarge")
if region_name == "ap-southeast-1":
    train_instance_type = "ml.g4dn.12xlarge"
if is_gcr:
    train_instance_type = "ml.g4dn.2xlarge"
logger.info(f"config.train_instance_type: {train_instance_type}")

comfy_async_ep_name = f"comfy-async-test-{current_time}"
comfy_real_time_ep_name = f"comfy-real-time-test-{current_time}"

compare_content = os.environ.get("COMPARE_CONTENT", "true")
logger.info(f"config.compare_content: {compare_content}")

webui_stack = "webui-stack"
comfy_stack = "comfy-stack"

role_sd_async = "sd_async"
role_sd_real_time = "sd_real_time"

role_comfy_async = "comfy_async"
role_comfy_real_time = "comfy_real_time"
