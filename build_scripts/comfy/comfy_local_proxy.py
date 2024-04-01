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


def execute_proxy(func):
    def wrapper(*args, **kwargs):
        number = server.PromptServer.instance.number
        executor = args[0]
        server_use = executor.server
        prompt = args[1]
        prompt_id = args[2]
        extra_data = args[3]
        payload = {
            "number": str(number),
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

        def send_execute(url, params):
            response = send_post_request(url, params=params)
            images_response = send_get_request(f"{api_url}/executes/{prompt_id}")
            save_files(images_response.json(), 'temp_files', 'temp')
            save_files(images_response.json(), 'output_files', 'output')
            return response

        with concurrent.futures.ThreadPoolExecutor() as executor:
            already_synced = False
            execute_future = executor.submit(send_execute, f"{api_url}/executes", payload)

            while comfy_need_sync and not execute_future.done():
                msg_future = executor.submit(send_get_request,
                                             f"{api_url}/sync/{prompt_id}")
                done, _ = concurrent.futures.wait([execute_future, msg_future],
                                                  return_when=concurrent.futures.FIRST_COMPLETED)

                for future in done:
                    if future == execute_future:
                        execute_resp = future.result()
                        if execute_resp.status_code == 200:
                            break
                        print(execute_resp)
                    elif future == msg_future:
                        msg_response = future.result()
                        print(msg_response)
                        if msg_response.status_code == 200:
                            if 'data' not in msg_response.json() or not msg_response.json().get("data"):
                                continue
                            already_synced = True
                            msg_array = msg_response.json().get("data")[0]
                            print(msg_array)
                            for msg in msg_array:
                                event = msg[0].get('event')
                                data = msg[0].get('data')
                                sid = msg[0].get('sid') if 'sid' in msg else None
                                server_use.send_sync(event, data, sid)

            while comfy_need_sync and not already_synced:
                msg_response = send_get_request(f"{api_url}/sync/{prompt_id}")
                print(msg_response)
                already_synced = True
                if msg_response.status_code == 200:
                    if 'data' not in msg_response.json() or not msg_response.json().get("data"):
                        continue
                    already_synced = True
                    msg_array = msg_response.json().get("data")[0]
                    print(msg_array)
                    for msg in msg_array:
                        event = msg[0].get('event')
                        data = msg[0].get('data')
                        sid = msg[0].get('sid') if 'sid' in msg else None
                        server_use.send_sync(event, data, sid)

    return wrapper


def save_files(execute, key, target_dir):
    if key in execute['data']:
        temp_files = execute['data'][key]
        for url in temp_files:
            loca_file = get_file_name(url)
            response = requests.get(url)
            # if target_dir not exists, create it
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            print(f"Saving file {loca_file} to {target_dir}")
            with open(f"./{target_dir}/{loca_file}", 'wb') as f:
                f.write(response.content)


def get_file_name(url: str):
    file_name = url.split('/')[-1]
    file_name = file_name.split('?')[0]
    return file_name


PromptExecutor.execute = execute_proxy(PromptExecutor.execute)


@server.PromptServer.instance.routes.post("/sync_outputs")
async def invocations(request):
    json_data = await request.json()
    print(json_data)
    prompt_id = json_data["prompt_id"]
    image_data = json_data.get('image_video_data', {})
    folder_path = f'{folder_paths.output_directory}/{prompt_id}'
    os.makedirs(folder_path, exist_ok=True)

    for image_name, encoded_image in image_data.items():
        image_path = os.path.join(folder_path, image_name)
        decoded_image = base64.b64decode(encoded_image)
        with open(image_path, 'wb') as image_file:
            print(f"saved image{decoded_image} to", image_path)
            image_file.write(decoded_image)

    return web.Response(status=200)


@server.PromptServer.instance.routes.post("/send_sync")
async def invocations(request):
    json_data = await request.json()
    print(json_data)
    event = json_data['event']
    data = json_data['data']
    sid = json_data['sid']
    server.PromptServer.instance.send_sync(event, data, sid)
    return web.Response(status=200)
