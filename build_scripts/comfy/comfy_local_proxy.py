import base64
import concurrent.futures
import os

import requests
from aiohttp import web

import folder_paths
import server
from execution import PromptExecutor


api_url = os.environ.get('COMFY_API_URL')
api_token = os.environ.get('COMFY_API_TOKEN')
comfy_endpoint = os.environ.get('COMFY_ENDPOINT', 'comfy-real-time-comfy')
comfy_need_sync = os.environ.get('COMFY_NEED_SYNC', False)
comfy_need_prepare = os.environ.get('COMFY_NEED_PREPARE', False)


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
            print("Missing prompt_id or image_video_data in the response.")
            return

        folder_path = os.path.join(local_folder, prompt_id)
        os.makedirs(folder_path, exist_ok=True)

        for image_name, image_url in image_video_data.items():
            image_response = requests.get(image_url)
            if image_response.status_code == 200:
                image_path = os.path.join(folder_path, image_name)
                with open(image_path, "wb") as image_file:
                    image_file.write(image_response.content)
                print(f"Image '{image_name}' saved to {image_path}")
            else:
                print(
                    f"Failed to download image '{image_name}' from {image_url}. Status code: {image_response.status_code}")

    except Exception as e:
        print(f"Error saving images locally: {e}")


def save_files(prefix, execute, key, target_dir, need_prefix):
    if key in execute['data']:
        temp_files = execute['data'][key]
        for url in temp_files:
            loca_file = get_file_name(url)
            response = requests.get(url)
            # if target_dir not exists, create it
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            print(f"Saving file {loca_file} to {target_dir}")
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
        event = msg[0].get('event')
        data = msg[0].get('data')
        sid = msg[0].get('sid') if 'sid' in msg else None
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
                            print(images_response.json())
                            save_already = True
                            break
                        print(execute_resp.json())
                    elif future == msg_future:
                        msg_response = future.result()
                        print(msg_response.json())
                        if msg_response.status_code == 200:
                            if 'data' not in msg_response.json() or not msg_response.json().get("data"):
                                continue
                            already_synced = True
                            handle_sync_messages(server_use, msg_response.json().get("data")[0])

            while comfy_need_sync and not already_synced:
                msg_response = send_get_request(f"{api_url}/sync/{prompt_id}")
                print(msg_response.json())
                already_synced = True
                if msg_response.status_code == 200:
                    if 'data' not in msg_response.json() or not msg_response.json().get("data"):
                        continue
                    already_synced = True
                    handle_sync_messages(server_use, msg_response.json().get("data")[0])

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
        print(f"Sending sync request!!!!!!! {args}")
        return func(*args, **kwargs)
    return wrapper


server.PromptServer.send_sync = send_sync_proxy(server.PromptServer.send_sync)

