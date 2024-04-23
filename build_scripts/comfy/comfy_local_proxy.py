import base64
import concurrent.futures
import datetime
import os
import signal
import sys
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
import fcntl
import hashlib

global sync_msg_list


env_path = '/etc/environment'

if 'ENV_FILE_PATH' in os.environ and os.environ.get('ENV_FILE_PATH'):
    env_path = os.environ.get('ENV_FILE_PATH')

load_dotenv('/etc/environment')
logging.info(f"env_path{env_path}")

env_keys = ['ENV_FILE_PATH', 'COMFY_INPUT_PATH', 'COMFY_MODEL_PATH', 'COMFY_NODE_PATH', 'COMFY_API_URL',
            'COMFY_API_TOKEN', 'COMFY_ENDPOINT', 'COMFY_NEED_SYNC', 'COMFY_NEED_PREPARE', 'COMFY_BUCKET_NAME',
            'MAX_WAIT_TIME', 'DISABLE_AWS_PROXY', 'DISABLE_AUTO_SYNC']

for item in os.environ.keys():
    if item in env_keys:
        logging.info(f'evn key： {item} {os.environ.get(item)}')

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
max_wait_time = os.environ.get('MAX_WAIT_TIME', 30)

no_need_sync_files = ['.autosave', '.cache', '.autosave1', '~', '.swp']


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


def calculate_file_hash(file_path):
    # 创建一个哈希对象
    hasher = hashlib.sha256()
    # 打开文件并逐块更新哈希对象
    with open(file_path, 'rb') as file:
        buffer = file.read(65536)  # 64KB 的缓冲区大小
        while len(buffer) > 0:
            hasher.update(buffer)
            buffer = file.read(65536)
    # 返回哈希值的十六进制表示
    return hasher.hexdigest()


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
    already_synced = False
    global sync_msg_list
    for msg in msg_array:
        for item in msg:
            event = item.get('event')
            data = item.get('data')
            sid = item.get('sid') if 'sid' in item else None
            if data in sync_msg_list:
                continue
            server_use.send_sync(event, data, sid)
            sync_msg_list.append(data)
            if event == 'finish':
                already_synced = True
            elif event == 'executed':
                already_synced = True
    return already_synced


def execute_proxy(func):
    def wrapper(*args, **kwargs):
        if os.environ.get('DISABLE_AWS_PROXY') == 'True':
            logging.info("disabled aws proxy, use local")
            return func(*args, **kwargs)
        logging.info("enable aws proxy, use aws")
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
            "multi_async": True
        }

        def send_post_request(url, params):
            response = requests.post(url, json=params, headers=headers)
            return response

        def send_get_request(url):
            response = requests.get(url, headers=headers)
            return response
        logging.debug(f"payload is: {payload}")

        already_synced = False
        save_already = False
        with concurrent.futures.ThreadPoolExecutor() as executor:
            execute_future = executor.submit(send_post_request, f"{api_url}/executes", payload)
            while comfy_need_sync and not execute_future.done():
                msg_future = executor.submit(send_get_request,
                                             f"{api_url}/sync/{prompt_id}")
                done, _ = concurrent.futures.wait([execute_future, msg_future],
                                                  return_when=concurrent.futures.FIRST_COMPLETED)
                global sync_msg_list
                sync_msg_list = []
                for future in done:
                    if future == execute_future:
                        execute_resp = future.result()
                        if execute_resp.status_code == 200 or execute_resp.status_code == 201 or execute_resp.status_code == 202:
                            i = max_wait_time
                            while i > 0:
                                images_response = send_get_request(f"{api_url}/executes/{prompt_id}")
                                response = images_response.json()
                                if 'data' not in response or not response['data'] or 'status' not in response['data'] or not response['data']['status']:
                                    logging.error("there is no response from execute result !!!!!!!!")
                                    break
                                elif response['data']['status'] != 'Completed' and response['data']['status'] != 'success':
                                    time.sleep(2)
                                    i = i - 1
                                else:
                                    save_files(prompt_id, images_response.json(), 'temp_files', 'temp', False)
                                    save_files(prompt_id, images_response.json(), 'output_files', 'output', True)
                                    logging.info(images_response.json())
                                    save_already = True
                                    break
                            break
                        logging.info(execute_resp.json())
                    elif future == msg_future:
                        msg_response = future.result()
                        logging.info(msg_response.json())
                        if msg_response.status_code == 200:
                            if 'data' not in msg_response.json() or not msg_response.json().get("data"):
                                logging.error("there is no response from sync msg by thread ")
                            else:
                                logging.debug(msg_response.json())
                                already_synced = handle_sync_messages(server_use, msg_response.json().get("data"))
            while comfy_need_sync and not already_synced:
                msg_response = send_get_request(f"{api_url}/sync/{prompt_id}")
                # logging.info(msg_response.json())
                already_synced = True
                if msg_response.status_code == 200:
                    if 'data' not in msg_response.json() or not msg_response.json().get("data"):
                        logging.error("there is no response from sync msg")
                    else:
                        logging.debug(msg_response.json())
                        already_synced = handle_sync_messages(server_use, msg_response.json().get("data"))

            if not save_already:
                execute_resp = execute_future.result()
                if execute_resp.status_code == 200 or execute_resp.status_code == 201 or execute_resp.status_code == 202:
                    i = max_wait_time
                    while i > 0:
                        images_response = send_get_request(f"{api_url}/executes/{prompt_id}")
                        response = images_response.json()
                        if images_response.status_code == 404:
                            time.sleep(3)
                            i = i - 2
                        elif 'data' not in response or not response['data'] or 'status' not in response['data'] or not response['data']['status']:
                            logging.error("there is no response from sync executes")
                            break
                        elif response['data']['status'] != 'Completed' and response['data']['status'] != 'success':
                            time.sleep(2)
                            i = i - 1
                        else:
                            save_files(prompt_id, images_response.json(), 'temp_files', 'temp', False)
                            save_files(prompt_id, images_response.json(), 'output_files', 'output', True)
                            break
    return wrapper


PromptExecutor.execute = execute_proxy(PromptExecutor.execute)


def send_sync_proxy(func):
    def wrapper(*args, **kwargs):
        logging.info(f"Sending sync request----- {args}")
        return func(*args, **kwargs)
    return wrapper


server.PromptServer.send_sync = send_sync_proxy(server.PromptServer.send_sync)


def sync_files(filepath, is_folder, is_auto):
    try:
        directory = os.path.dirname(filepath)
        logging.info(f"Directory changed in: {directory} {filepath}")
        if not directory:
            logging.info("root path no need to sync files by duplicate opt")
            return None
        logging.info(f"Files changed in: {filepath}")
        timestamp = str(int(time.time() * 1000))
        need_prepare = False
        prepare_type = 'default'
        need_reboot = False
        for ignore_item in no_need_sync_files:
            if filepath.endswith(ignore_item):
                logging.info(f"no need to sync files by ignore files {filepath} ends by {ignore_item}")
                return None
        if (str(directory).endswith(f"{DIR2}" if DIR2.startswith("/") else f"/{DIR2}")
                or str(filepath) == DIR2 or str(filepath) == f'./{DIR2}' or f"{DIR2}/" in filepath):
            logging.info(f" sync custom nodes files: {filepath}")
            s5cmd_syn_node_command = f's5cmd --log=error sync {DIR2}/ "s3://{bucket_name}/comfy/{comfy_endpoint}/{timestamp}/custom_nodes/"'
            # s5cmd_syn_node_command = f'aws s3 sync {DIR2}/ "s3://{bucket_name}/comfy/{comfy_endpoint}/{timestamp}/custom_nodes/"'
            # s5cmd_syn_node_command = f's5cmd sync {DIR2}/* "s3://{bucket_name}/comfy/{comfy_endpoint}/{timestamp}/custom_nodes/"'

            # custom_node文件夹有变化 稍后再同步
            if is_auto and not is_folder_unlocked(directory):
                logging.info("sync custom_nodes files is changing ,waiting.... ")
                return None
            logging.info("sync custom_nodes files start")
            logging.info(s5cmd_syn_node_command)
            os.system(s5cmd_syn_node_command)
            need_prepare = True
            need_reboot = True
            prepare_type = 'nodes'
        elif (str(directory).endswith(f"{DIR3}" if DIR3.startswith("/") else f"/{DIR3}")
              or str(filepath) == DIR3 or str(filepath) == f'./{DIR3}' or f"{DIR3}/" in filepath):
            logging.info(f" sync input files: {filepath}")
            s5cmd_syn_input_command = f's5cmd --log=error sync {DIR3}/ "s3://{bucket_name}/comfy/{comfy_endpoint}/{timestamp}/input/"'

            # 判断文件写完后再同步
            if is_auto:
                if bool(is_folder):
                    can_sync = is_folder_unlocked(filepath)
                else:
                    can_sync = is_file_unlocked(filepath)
                if not can_sync:
                    logging.info("sync input files is changing ,waiting.... ")
                    return None
            logging.info("sync input files start")
            logging.info(s5cmd_syn_input_command)
            os.system(s5cmd_syn_input_command)
            need_prepare = True
            prepare_type = 'inputs'
        elif (str(directory).endswith(f"{DIR1}" if DIR1.startswith("/") else f"/{DIR1}")
              or str(filepath) == DIR1 or str(filepath) == f'./{DIR1}' or f"{DIR1}/" in filepath):
            logging.info(f" sync models files: {filepath}")
            s5cmd_syn_model_command = f's5cmd --log=error sync {DIR1}/ "s3://{bucket_name}/comfy/{comfy_endpoint}/{timestamp}/models/"'

            # 判断文件写完后再同步
            if is_auto:
                if bool(is_folder):
                    can_sync = is_folder_unlocked(filepath)
                else:
                    can_sync = is_file_unlocked(filepath)
                # logging.info(f'is folder {directory} {is_folder} can_sync {can_sync}')
                if not can_sync:
                    logging.info("sync input models is changing ,waiting.... ")
                    return None

            logging.info("sync models files start")
            logging.info(s5cmd_syn_model_command)
            os.system(s5cmd_syn_model_command)
            need_prepare = True
            prepare_type = 'models'
        logging.info(f"Files changed in:: {need_prepare} {str(directory)} {DIR2} {DIR1} {DIR3}")
        if need_prepare:
            url = api_url + "prepare"
            logging.info(f"URL:{url}")
            data = {"endpoint_name": comfy_endpoint, "need_reboot": need_reboot, "prepare_id": timestamp,
                    "prepare_type": prepare_type}
            logging.info(f"prepare params Data: {json.dumps(data, indent=4)}")
            result = subprocess.run(["curl", "--location", "--request", "POST", url, "--header",
                                     f"x-api-key: {api_token}", "--data-raw", json.dumps(data)],
                                    capture_output=True, text=True)
            logging.info(result.stdout)
            return result.stdout
        return None
    except Exception as e:
        logging.info(f"sync_files error {e}")
        return None


def is_folder_unlocked(directory):
    # logging.info("check if folder ")
    event_handler = MyHandlerWithCheck()
    observer = Observer()
    observer.schedule(event_handler, directory, recursive=True)
    observer.start()
    time.sleep(1)
    result = False
    try:
        if event_handler.file_changed:
            logging.info(f"folder {directory} is still changing..")
            event_handler.file_changed = False
            time.sleep(1)
            if event_handler.file_changed:
                logging.info(f"folder {directory} is still still changing..")
            else:
                logging.info(f"folder {directory} changing stopped")
                result = True
        else:
            logging.info(f"folder {directory} not stopped")
            result = True
    except (KeyboardInterrupt, Exception) as e:
        logging.info(f"folder {directory} changed exception {e}")
    observer.stop()
    return result


def is_file_unlocked(file_path):
    # logging.info("check if file ")
    try:
        initial_size = os.path.getsize(file_path)
        initial_mtime = os.path.getmtime(file_path)
        time.sleep(1)

        current_size = os.path.getsize(file_path)
        current_mtime = os.path.getmtime(file_path)
        if current_size != initial_size or current_mtime != initial_mtime:
            logging.info(f"unlock file error {file_path} is changing")
            return False

        with open(file_path, 'r') as f:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
    except (IOError, OSError, Exception) as e:
        logging.info(f"unlock file error {file_path} is writing")
        logging.error(e)
        return False


class MyHandlerWithCheck(FileSystemEventHandler):
    def __init__(self):
        self.file_changed = False

    def on_modified(self, event):
        logging.info(f"custom_node folder is changing {event.src_path}")
        self.file_changed = True

    def on_deleted(self, event):
        logging.info(f"custom_node folder is changing {event.src_path}")
        self.file_changed = True

    def on_created(self, event):
        logging.info(f"custom_node folder is changing {event.src_path}")
        self.file_changed = True


class MyHandlerWithSync(FileSystemEventHandler):
    def on_modified(self, event):
        logging.info(f"{datetime.datetime.now()} files modified ，start to sync {event}")
        sync_files(event.src_path, event.is_directory, True)

    def on_created(self, event):
        logging.info(f"{datetime.datetime.now()} files added ，start to sync {event}")
        sync_files(event.src_path, event.is_directory, True)

    def on_deleted(self, event):
        logging.info(f"{datetime.datetime.now()} files deleted ，start to sync {event}")
        sync_files(event.src_path, event.is_directory, True)


stop_event = threading.Event()


def check_and_sync():
    logging.info("check_and_sync start")
    event_handler = MyHandlerWithSync()
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


if os.environ.get('DISABLE_AUTO_SYNC') == 'false':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    check_sync_thread = threading.Thread(target=check_and_sync)
    check_sync_thread.start()


@server.PromptServer.instance.routes.get("/reboot")
async def restart(self):
    logging.info(f"start to reboot {self}")
    try:
        sys.stdout.close_log()
    except Exception as e:
        logging.info(f"error reboot  {e}")
        pass
    return os.execv(sys.executable, [sys.executable] + sys.argv)


@server.PromptServer.instance.routes.post("/sync_env")
async def sync_env(request):
    logging.info(f"start to sync_env {request}")
    try:
        result1 = sync_files(f'./{DIR1}', 'False', False)
        result2 = sync_files(f'./{DIR2}', 'True', False)
        result3 = sync_files(f'./{DIR3}', 'False', False)
        logging.info(f"sync result is :{result1} {result2} {result3}")
        return True
    except Exception as e:
        logging.info(f"error sync_env {e}")
        pass
    return False


@server.PromptServer.instance.routes.post("/change_env")
async def change_env(request):
    logging.info(f"start to change_env {request}")
    json_data = await request.json()
    if 'DISABLE_AWS_PROXY' in json_data and json_data['DISABLE_AWS_PROXY'] is not None:
        logging.info(f"origin evn key DISABLE_AWS_PROXY is :{os.environ.get('DISABLE_AWS_PROXY')} {str(json_data['DISABLE_AWS_PROXY'])}")
        os.environ['DISABLE_AWS_PROXY'] = str(json_data['DISABLE_AWS_PROXY'])
        logging.info(f"now evn key DISABLE_AWS_PROXY is :{os.environ.get('DISABLE_AWS_PROXY')}")
    return True
