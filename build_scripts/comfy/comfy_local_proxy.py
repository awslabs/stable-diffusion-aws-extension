import base64
import concurrent.futures
import os
import signal
import threading

import requests
from aiohttp import web

import folder_paths
import server
from execution import PromptExecutor

import time
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
from dotenv import load_dotenv
import logging


env_path = '/etc/environment'

if 'ENV_FILE_PATH' in os.environ and os.environ.get('ENV_FILE_PATH'):
    env_path = os.environ.get('ENV_FILE_PATH')

load_dotenv('/etc/environment')
logging.info("env_path", env_path)

for item in os.environ.keys():
    logging.info(f'环境变量： {item} {os.environ.get(item)}')

DIR3 = "input"
DIR1 = "models"
DIR2 = "custom_nodes"

if 'COMFY_INPUT_PATH' in os.environ and os.environ.get('COMFY_INPUT_PATH'):
    DIR3 = os.environ.get('COMFY_INPUT_PATH')
if 'COMFY_MODEL_PATH' in os.environ and os.environ.get('COMFY_MODEL_PATH'):
    DIR1 = os.environ.get('COMFY_MODEL_PATH')
if 'COMFY_NODE_PATH' in os.environ and os.environ.get('COMFY_NODE_PATH'):
    DIR2 = os.environ.get('COMFY_NODE_PATH')


api_url = os.environ.get('COMFY_API_URL')
api_token = os.environ.get('COMFY_API_TOKEN')
comfy_endpoint = os.environ.get('COMFY_ENDPOINT', 'comfy-real-time-comfy')
comfy_need_sync = os.environ.get('COMFY_NEED_SYNC', False)
comfy_need_prepare = os.environ.get('COMFY_NEED_PREPARE', False)
bucket_name = os.environ.get('COMFY_BUCKET_NAME')


if not api_url:
    raise ValueError("API_URL environment variables must be set.")

if not api_token:
    raise ValueError("API_TOKEN environment variables must be set.")

if not comfy_endpoint:
    raise ValueError("COMFY_ENDPOINT environment variables must be set.")

headers = {"x-api-key": api_token, "Content-Type": "application/json"}


def save_images_locally(response_json, local_folder):
    try:
        data = response_json.get("data", {})
        prompt_id = data.get("prompt_id")
        image_video_data = data.get("image_video_data", {})

        if not prompt_id or not image_video_data:
            logging.info("Missing prompt_id or image_video_data in the response.")
            return

        folder_path = os.path.join(local_folder, prompt_id)
        os.makedirs(folder_path, exist_ok=True)

        for image_name, image_url in image_video_data.items():
            image_response = requests.get(image_url)
            if image_response.status_code == 200:
                image_path = os.path.join(folder_path, image_name)
                with open(image_path, "wb") as image_file:
                    image_file.write(image_response.content)
                logging.info(f"Image '{image_name}' saved to {image_path}")
            else:
                logging.info(
                    f"Failed to download image '{image_name}' from {image_url}. Status code: {image_response.status_code}")

    except Exception as e:
        logging.info(f"Error saving images locally: {e}")


def save_files(prefix, execute, key, target_dir, need_prefix):
    if key in execute['data']:
        temp_files = execute['data'][key]
        for url in temp_files:
            loca_file = get_file_name(url)
            response = requests.get(url)
            # if target_dir not exists, create it
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            logging.info(f"Saving file {loca_file} to {target_dir}")
            if loca_file.endswith("output_images_will_be_put_here"):
                continue
            if need_prefix:
                with open(f"./{target_dir}/{prefix}_{loca_file}", 'wb') as f:
                    f.write(response.content)
            else:
                with open(f"./{target_dir}/{loca_file}", 'wb') as f:
                    f.write(response.content)


def get_file_name(url: str):
    file_name = url.split('/')[-1]
    file_name = file_name.split('?')[0]
    return file_name


def handle_sync_messages(server_use, msg_array):
    for msg in msg_array:
        for item in msg:
            event = item.get('event')
            data = item.get('data')
            sid = item.get('sid') if 'sid' in item else None
            server_use.send_sync(event, data, sid)


def execute_proxy(func):
    def wrapper(*args, **kwargs):
        executor = args[0]
        server_use = executor.server
        prompt = args[1]
        prompt_id = args[2]
        extra_data = args[3]

        payload = {
            "number": str(server.PromptServer.instance.number),
            "prompt": prompt,
            "prompt_id": prompt_id,
            "extra_data": extra_data,
            "endpoint_name": comfy_endpoint,
            "need_prepare": comfy_need_prepare,
            "need_sync": comfy_need_sync,
        }

        def send_post_request(url, params):
            response = requests.post(url, json=params, headers=headers)
            return response

        def send_get_request(url):
            response = requests.get(url, headers=headers)
            return response

        already_synced = False
        save_already = False
        with concurrent.futures.ThreadPoolExecutor() as executor:
            execute_future = executor.submit(send_post_request, f"{api_url}/executes", payload)
            while comfy_need_sync and not execute_future.done():
                msg_future = executor.submit(send_get_request,
                                             f"{api_url}/sync/{prompt_id}")
                done, _ = concurrent.futures.wait([execute_future, msg_future],
                                                  return_when=concurrent.futures.FIRST_COMPLETED)
                for future in done:
                    if future == execute_future:
                        execute_resp = future.result()
                        if execute_resp.status_code == 200:
                            images_response = send_get_request(f"{api_url}/executes/{prompt_id}")
                            save_files(prompt_id, images_response.json(), 'temp_files', 'temp', False)
                            save_files(prompt_id, images_response.json(), 'output_files', 'output', True)
                            logging.info(images_response.json())
                            save_already = True
                            break
                        logging.info(execute_resp.json())
                    elif future == msg_future:
                        msg_response = future.result()
                        logging.info(msg_response.json())
                        if msg_response.status_code == 200:
                            if 'data' not in msg_response.json() or not msg_response.json().get("data"):
                                continue
                            logging.debug(msg_response.json())
                            # if 'event' in msg_response.json() and msg_response.json().get("event") == 'finish':
                            #     already_synced = True
                            # else:
                            #     continue
                            already_synced = True
                            handle_sync_messages(server_use, msg_response.json().get("data"))

            while comfy_need_sync and not already_synced:
                msg_response = send_get_request(f"{api_url}/sync/{prompt_id}")
                logging.info(msg_response.json())
                already_synced = True
                if msg_response.status_code == 200:
                    if 'data' not in msg_response.json() or not msg_response.json().get("data"):
                        continue
                    # if 'event' in msg_response.json() and msg_response.json().get("event") == 'finish':
                    #     already_synced = True
                    # else:
                    #     continue
                    already_synced = True
                    handle_sync_messages(server_use, msg_response.json().get("data"))

            if not save_already:
                execute_resp = execute_future.result()
                if execute_resp.status_code == 200:
                    images_response = send_get_request(f"{api_url}/executes/{prompt_id}")
                    save_files(prompt_id, images_response.json(), 'temp_files', 'temp', False)
                    save_files(prompt_id, images_response.json(), 'output_files', 'output', True)

    return wrapper


PromptExecutor.execute = execute_proxy(PromptExecutor.execute)


def send_sync_proxy(func):
    def wrapper(*args, **kwargs):
        logging.info(f"Sending sync request!!!!!!! {args}")
        return func(*args, **kwargs)
    return wrapper


server.PromptServer.send_sync = send_sync_proxy(server.PromptServer.send_sync)


def sync_files(filepath):
    try:
        directory = os.path.dirname(filepath)
        logging.info(f"Directory changed in: {directory}")
        logging.info(f"Files changed in: {filepath}")
        timestamp = str(int(time.time() * 1000))
        need_prepare = False

        if (str(directory).endswith(f"{DIR2}" if DIR2.startswith("/") else f"/{DIR2}")
                or str(filepath) == DIR2):
            logging.info(f" sync custom nodes files: {filepath}")
            s5cmd_syn_node_command = f's5cmd sync {DIR2}/ "s3://{bucket_name}/comfy/{comfy_endpoint}/{timestamp}/custom_nodes/"'
            # s5cmd_syn_node_command = f'aws s3 sync {DIR2}/ "s3://{bucket_name}/comfy/{comfy_endpoint}/{timestamp}/custom_nodes/"'
            # s5cmd_syn_node_command = f's5cmd sync {DIR2}/* "s3://{bucket_name}/comfy/{comfy_endpoint}/{timestamp}/custom_nodes/"'
            logging.info(s5cmd_syn_node_command)
            os.system(s5cmd_syn_node_command)
            need_prepare = True
        elif (str(directory).endswith(f"{DIR3}" if DIR3.startswith("/") else f"/{DIR3}")
              or str(filepath) == DIR3):
            logging.info(f" sync custom input files: {filepath}")
            s5cmd_syn_input_command = f's5cmd sync {DIR3}/ "s3://{bucket_name}/comfy/{comfy_endpoint}/{timestamp}/input/"'
            logging.info(s5cmd_syn_input_command)
            os.system(s5cmd_syn_input_command)
            need_prepare = True
        elif (str(directory).endswith(f"{DIR1}" if DIR1.startswith("/") else f"/{DIR1}")
              or str(filepath) == DIR1):
            logging.info(f" sync custom models files: {filepath}")
            s5cmd_syn_model_command = f's5cmd sync {DIR1}/ "s3://{bucket_name}/comfy/{comfy_endpoint}/{timestamp}/models/"'
            logging.info(s5cmd_syn_model_command)
            os.system(s5cmd_syn_model_command)
            need_prepare = True
        logging.info(f"Files changed in:: {need_prepare} {str(directory)} {DIR2} {DIR1} {DIR3}")
        if need_prepare:
            url = api_url + "prepare"
            logging.info(f"URL:{url}")
            data = {"endpoint_name": comfy_endpoint, "need_reboot": True, "prepare_id": timestamp}
            logging.info(f"prepare params Data: {json.dumps(data, indent=4)}")
            result = subprocess.run(["curl", "--location", "--request", "POST", url, "--header",
                                     f"x-api-key: {api_token}", "--data-raw", json.dumps(data)],
                                    capture_output=True, text=True)
            logging.info(result.stdout)
    except Exception as e:
        logging.info(f"sync_files error {e}")


class MyHandler(FileSystemEventHandler):
    def on_modified(self, event):
        sync_files(event.src_path)

    def on_created(self, event):
        sync_files(event.src_path)

    def on_deleted(self, event):
        sync_files(event.src_path)


stop_event = threading.Event()


def check_and_sync():
    logging.info("check_and_sync start")
    event_handler = MyHandler()
    observer = Observer()
    try:
        observer.schedule(event_handler, DIR1, recursive=True)
        observer.schedule(event_handler, DIR2, recursive=True)
        observer.schedule(event_handler, DIR3, recursive=True)
        observer.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("sync Shutting down please restart ComfyUI")
        observer.stop()
    observer.join()


def signal_handler(sig, frame):
    logging.info("Received termination signal. Exiting...")
    stop_event.set()


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

check_sync_thread = threading.Thread(target=check_and_sync)
check_sync_thread.start()



