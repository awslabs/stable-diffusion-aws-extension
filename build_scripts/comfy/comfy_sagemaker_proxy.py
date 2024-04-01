import base64
import datetime
import json
import logging
import os
import tarfile
import time
from dataclasses import dataclass
from typing import Optional

import boto3
import execution
import server
from aiohttp import web
from boto3.dynamodb.conditions import Key

global need_sync
global prompt_id

REGION = os.environ.get('AWS_REGION')
BUCKET = os.environ.get('BUCKET_NAME')
QUEUE_URL = os.environ.get('COMFY_QUEUE_URL')

GEN_INSTANCE_ID = os.environ.get('ENDPOINT_INSTANCE_ID')
ENDPOINT_NAME = os.environ.get('ENDPOINT_NAME')
ENDPOINT_ID = os.environ.get('ENDPOINT_ID')

INSTANCE_MONITOR_TABLE_NAME = os.environ.get('COMFY_INSTANCE_MONITOR_TABLE')
SYNC_TABLE_NAME = os.environ.get('COMFY_SYNC_TABLE')

dynamodb = boto3.resource('dynamodb', region_name=REGION)
sync_table = dynamodb.Table(SYNC_TABLE_NAME)
instance_monitor_table = dynamodb.Table(INSTANCE_MONITOR_TABLE_NAME)

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.INFO)


@dataclass
class ComfyResponse:
    statusCode: int
    message: str
    body: Optional[dict]


def ok(body: dict):
    return web.Response(status=200, content_type='application/json', body=json.dumps(body))


def error(body: dict):
    return web.Response(status=500, content_type='application/json', body=json.dumps(body))


async def prepare_comfy_env(sync_item: dict):
    try:
        request_id = sync_item['request_id']
        logger.info(f"prepare_environment start sync_item:{sync_item}")
        prepare_type = sync_item['prepare_type']
        rlt = True
        if prepare_type in ['default', 'models']:
            sync_models_rlt = sync_s3_files_or_folders_to_local(f'{request_id}/models/*', '/home/ubuntu/models', False)
            if not sync_models_rlt:
                rlt = False
        if prepare_type in ['default', 'inputs']:
            sync_inputs_rlt = sync_s3_files_or_folders_to_local(f'{request_id}/input/*', '/home/ubuntu/input', False)
            if not sync_inputs_rlt:
                rlt = False
        if prepare_type in ['default', 'nodes']:
            sync_nodes_rlt = sync_s3_files_or_folders_to_local(f'{request_id}/custom_nodes', '/home/ubuntu/custom_nodes', True)
            if not sync_nodes_rlt:
                rlt = False
        if prepare_type == 'custom':
            sync_source_path = sync_item['s3_source_path']
            local_target_path = sync_item['local_target_path']
            if not sync_source_path or not local_target_path:
                logger.info("s3_source_path and local_target_path should not be empty")
            else:
                sync_rlt = sync_s3_files_or_folders_to_local(sync_source_path,
                                                  f'/home/ubuntu/{local_target_path}', False)
                if not sync_rlt:
                    rlt = False
        elif prepare_type == 'other':
            sync_script = sync_item['sync_script']
            logger.info("sync_script")
            # sync_script.startswith('s5cmd') 不允许
            try:
                if sync_script and (sync_script.startswith("pip install") or sync_script.startswith("apt-get")
                                    or sync_script.startswith("os.environ")):
                    os.system(sync_script)
            except Exception as e:
                logger.error(f"Exception while execute sync_scripts : {sync_script}")
                rlt = False
        need_reboot = True if ('need_reboot' in sync_item and sync_item['need_reboot']
                               and str(sync_item['need_reboot']).lower() == 'true')else False
        if need_reboot:
            os.environ['NEED_REBOOT'] = 'true'
        else:
            os.environ['NEED_REBOOT'] = 'false'
        logger.info("prepare_environment end")
        os.environ['LAST_SYNC_REQUEST_ID'] = sync_item['request_id']
        os.environ['LAST_SYNC_REQUEST_TIME'] = sync_item['request_time']
        return rlt
    except Exception as e:
        return False


# def create_tar_gz(source_file, target_tar_gz):
#     # Example usage:
#     # source_file_path = "/path/to/your/source/file.txt"
#     # target_tar_gz_path = "/path/to/your/target/file.tar.gz"
#     with tarfile.open(target_tar_gz, "w:gz") as tar:
#         tar.add(source_file, arcname=os.path.basename(source_file))


def sync_s3_files_or_folders_to_local(s3_path, local_path, need_un_tar):
    logger.info("sync_s3_models_or_inputs_to_local start")
    # s5cmd_command = f'/home/ubuntu/tools/s5cmd cp "s3://{bucket_name}/{s3_path}/*" "{local_path}/"'
    s5cmd_command = f's5cmd sync "s3://{BUCKET}/comfy/{ENDPOINT_NAME}/{s3_path}" "{local_path}/"'
    try:
        # TODO 注意添加去重逻辑
        # TODO 注意记录更新信息 避免冲突或者环境改坏被误会
        logger.info(s5cmd_command)
        os.system(s5cmd_command)
        logger.info(f'Files copied from "s3://{BUCKET}/comfy/{ENDPOINT_NAME}/{s3_path}" to "{local_path}/"')
        if need_un_tar:
            for filename in os.listdir(local_path):
                if filename.endswith(".tar.gz"):
                    tar_filepath = os.path.join(local_path, filename)
                    with tarfile.open(tar_filepath, "r:gz") as tar:
                        tar.extractall(path=local_path)
                    os.remove(tar_filepath)
                    logger.info(f'File {tar_filepath} extracted and removed')
        return True
    except Exception as e:
        logger.info(f"Error executing s5cmd command: {e}")
        return False


def sync_local_outputs_to_s3(s3_path, local_path):
    logger.info("sync_local_outputs_to_s3 start")
    s5cmd_command = f's5cmd cp "{local_path}/*" "s3://{BUCKET}/comfy/{s3_path}/" '
    try:
        logger.info(s5cmd_command)
        os.system(s5cmd_command)
        logger.info(f'Files copied local to "s3://{BUCKET}/comfy/{s3_path}/" to "{local_path}/"')
        clean_cmd = f'rm -rf {local_path}'
        os.system(clean_cmd)
        logger.info(f'Files removed from local {local_path}')
    except Exception as e:
        logger.info(f"Error executing s5cmd command: {e}")


def sync_local_outputs_to_base64(local_path):
    logger.info("sync_local_outputs_to_base64 start")
    try:
        result = {}
        for root, dirs, files in os.walk(local_path):
            for file in files:
                file_path = os.path.join(root, file)
                with open(file_path, "rb") as f:
                    file_content = f.read()
                    base64_content = base64.b64encode(file_content).decode('utf-8')
                    result[file] = base64_content
        clean_cmd = f'rm -rf {local_path}'
        os.system(clean_cmd)
        logger.info(f'Files removed from local {local_path}')
        return result
    except Exception as e:
        logger.info(f"Error executing s5cmd command: {e}")
        return {}


@server.PromptServer.instance.routes.post("/invocations")
async def invocations(request):
    # response_body = {
    #     "prompt_id": '11111111-1111-1111',
    #     "instance_id": GEN_INSTANCE_ID,
    #     "status": "success",
    #     "output_path": f's3://{BUCKET}/comfy/output/11111111-1111-1111',
    #     "temp_path": f's3://{BUCKET}/comfy/temp/11111111-1111-1111',
    # }
    # return ok(response_body)
    # TODO serve 级别加锁
    json_data = await request.json()
    logger.info(f"invocations start json_data:{json_data}")
    global need_sync
    need_sync = json_data["need_sync"]
    global prompt_id
    prompt_id = json_data["prompt_id"]
    try:
        logger.info(
            f'bucket_name: {BUCKET}, region: {REGION}')
        if ('need_prepare' in json_data and json_data['need_prepare']
                and 'prepare_props' in json_data and json_data['prepare_props']):
            sync_already = await prepare_comfy_env(json_data['prepare_props'])
            if not sync_already:
                resp = {"prompt_id": prompt_id, "instance_id": GEN_INSTANCE_ID, "status": "fail",
                        "message": "the environment is not ready with sync"}
                return error(resp)
        server_instance = server.PromptServer.instance
        if "number" in json_data:
            number = float(json_data['number'])
            server_instance.number = number
        else:
            number = server_instance.number
            if "front" in json_data:
                if json_data['front']:
                    number = -number
            server_instance.number += 1
        valid = execution.validate_prompt(json_data['prompt'])
        if not valid[0]:
            resp = {"prompt_id": prompt_id, "instance_id": GEN_INSTANCE_ID, "status": "fail",
                    "message": "the environment is not ready valid[0] is false, need to resync"}
            return error(resp)
        extra_data = {}
        if "extra_data" in json_data:
            extra_data = json_data["extra_data"]
        if "client_id" in json_data:
            extra_data["client_id"] = json_data["client_id"]

        prompt_id = json_data['prompt_id']
        e = execution.PromptExecutor(server_instance)
        outputs_to_execute = valid[2]
        e.execute(json_data['prompt'], prompt_id, extra_data, outputs_to_execute)

        sync_local_outputs_to_s3(f'output/{prompt_id}', '/home/ubuntu/output')
        sync_local_outputs_to_s3(f'temp/{prompt_id}', '/home/ubuntu/temp')
        response_body = {
            "prompt_id": prompt_id,
            "instance_id": GEN_INSTANCE_ID,
            "status": "success",
            "output_path": f's3://{BUCKET}/comfy/output/{prompt_id}',
            "temp_path": f's3://{BUCKET}/comfy/temp/{prompt_id}',
        }
        return ok(response_body)
    except Exception as e:
        logger.info("exception occurred", e)
        resp = {"prompt_id": prompt_id, "instance_id": GEN_INSTANCE_ID, "status": "fail",
                "message": f"exception occurred {e}"}
        return error(resp)


def get_last_ddb_sync_record():
    sync_response = sync_table.query(
        KeyConditionExpression=Key('endpoint_name').eq(ENDPOINT_NAME),
        Limit=1,
        ScanIndexForward=False
    )
    latest_sync_record = sync_response['Items'][0] if ('Items' in sync_response
                                                       and len(sync_response['Items']) > 0) else None
    if latest_sync_record:
        logger.info(f"latest_sync_record is：{latest_sync_record}")
        return latest_sync_record

    logger.info("no latest_sync_record found")
    return None


def get_latest_ddb_instance_monitor_record():
    key_condition_expression = ('endpoint_name = :endpoint_name_val '
                                'AND gen_instance_id = :gen_instance_id_val')
    expression_attribute_values = {
        ':endpoint_name_val': ENDPOINT_NAME,
        ':gen_instance_id_val': GEN_INSTANCE_ID
    }
    instance_monitor_response = instance_monitor_table.query(
        KeyConditionExpression=key_condition_expression,
        ExpressionAttributeValues=expression_attribute_values
    )
    instance_monitor_record = instance_monitor_response['Items'][0] \
        if ('Items' in instance_monitor_response and len(instance_monitor_response['Items']) > 0) else None

    if instance_monitor_record:
        logger.info(f"instance_monitor_record is {instance_monitor_record}")
        return instance_monitor_record

    logger.info("no instance_monitor_record found")
    return None


def save_sync_instance_monitor(last_sync_request_id: str, sync_status: str):
    item = {
        'endpoint_id': ENDPOINT_ID,
        'endpoint_name': ENDPOINT_NAME,
        'gen_instance_id': GEN_INSTANCE_ID,
        'sync_status': sync_status,
        'last_sync_request_id': last_sync_request_id,
        'last_sync_time': datetime.datetime.now().isoformat(),
        'sync_list': [],
        'create_time': datetime.datetime.now().isoformat(),
        'last_heartbeat_time': datetime.datetime.now().isoformat()
    }
    save_resp = instance_monitor_table.put_item(Item=item)
    logger.info(f"save instance item {save_resp}")
    return save_resp


def update_sync_instance_monitor(instance_monitor_record):
    # 更新记录
    update_expression = ("SET sync_status = :new_sync_status, last_sync_request_id = :sync_request_id, "
                         "sync_list = :sync_list, last_sync_time = :sync_time, last_heartbeat_time = :heartbeat_time")
    expression_attribute_values = {
        ":new_sync_status": instance_monitor_record['sync_status'],
        ":sync_request_id": instance_monitor_record['last_sync_request_id'],
        ":sync_list": instance_monitor_record['sync_list'],
        ":sync_time": datetime.datetime.now().isoformat(),
        ":heartbeat_time": datetime.datetime.now().isoformat(),
    }

    response = instance_monitor_table.update_item(
        Key={'endpoint_name': ENDPOINT_NAME,
             'gen_instance_id': GEN_INSTANCE_ID},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_attribute_values
    )
    logger.info(f"update_sync_instance_monitor :{response}")
    return response


def sync_instance_monitor_status(need_save: bool):
    try:
        logger.info(f"sync_instance_monitor_status {datetime.datetime.now()}")
        if need_save:
            save_sync_instance_monitor('', 'init')
        else:
            update_expression = ("SET last_heartbeat_time = :heartbeat_time")
            expression_attribute_values = {
                ":heartbeat_time": datetime.datetime.now().isoformat(),
            }
            instance_monitor_table.update_item(
                Key={'endpoint_name': ENDPOINT_NAME,
                     'gen_instance_id': GEN_INSTANCE_ID},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values
            )
    except Exception as e:
        logger.info(f"sync_instance_monitor_status error :{e}")


# must be sync invoke and use the env to check
@server.PromptServer.instance.routes.post("/sync_instance")
async def sync_instance(request):
    if 'ALREADY_SYNC' in os.environ and os.environ.get('ALREADY_SYNC').lower() == 'false':
        resp = {"status": "success", "message": "syncing"}
        return ok(resp)

    os.environ['ALREADY_SYNC'] = 'false'
    logger.info(f"sync_instance start ！！ {datetime.datetime.now().isoformat()} {request}")
    try:
        last_sync_record = get_last_ddb_sync_record()
        if not last_sync_record:
            logger.info("no last sync record found do not need sync")
            sync_instance_monitor_status(True)
            resp = {"status": "success", "message": "no sync"}
            os.environ['ALREADY_SYNC'] = 'true'
            return ok(resp)

        if ('request_id' in last_sync_record and last_sync_record['request_id']
                and os.environ.get('LAST_SYNC_REQUEST_ID')
                and os.environ.get('LAST_SYNC_REQUEST_ID') == last_sync_record['request_id']
                and os.environ.get('LAST_SYNC_REQUEST_TIME')
                and os.environ.get('LAST_SYNC_REQUEST_TIME') == last_sync_record['request_time']):
            logger.info("last sync record already sync by os check")
            sync_instance_monitor_status(False)
            resp = {"status": "success", "message": "no sync env"}
            os.environ['ALREADY_SYNC'] = 'true'
            return ok(resp)

        instance_monitor_record = get_latest_ddb_instance_monitor_record()
        if not instance_monitor_record:
            sync_already = await prepare_comfy_env(last_sync_record)
            if sync_already:
                logger.info("should init prepare instance_monitor_record")
                sync_status = 'success' if sync_already else 'failed'
                save_sync_instance_monitor(last_sync_record['request_id'], sync_status)
            else:
                sync_instance_monitor_status(False)
        else:
            if ('last_sync_request_id' in instance_monitor_record
                    and instance_monitor_record['last_sync_request_id']
                    and instance_monitor_record['last_sync_request_id'] == last_sync_record['request_id']
                    and instance_monitor_record['sync_status']
                    and instance_monitor_record['sync_status'] == 'success'):
                logger.info("last sync record already sync")
                sync_instance_monitor_status(False)
                resp = {"status": "success", "message": "no sync ddb"}
                os.environ['ALREADY_SYNC'] = 'true'
                return ok(resp)

            sync_already = await prepare_comfy_env(last_sync_record)
            instance_monitor_record['sync_status'] = 'success' if sync_already else 'failed'
            instance_monitor_record['last_sync_request_id'] = last_sync_record['request_id']
            sync_list = instance_monitor_record['sync_list'] if ('sync_list' in instance_monitor_record
                                                                 and instance_monitor_record['sync_list']) else []
            sync_list.append(last_sync_record['request_id'])

            instance_monitor_record['sync_list'] = sync_list
            logger.info("should update prepare instance_monitor_record")
            update_sync_instance_monitor(instance_monitor_record)
        os.environ['ALREADY_SYNC'] = 'true'
        resp = {"status": "success", "message": "sync"}
        return ok(resp)
    except Exception as e:
        logger.info("exception occurred", e)
        os.environ['ALREADY_SYNC'] = 'true'
        resp = {"status": "fail", "message": "sync"}
        return error(resp)


def validate_prompt_proxy(func):
    def wrapper(*args, **kwargs):
        # 在这里添加您的代理逻辑
        logger.info("validate_prompt_proxy start...")
        # 调用原始函数
        result = func(*args, **kwargs)
        # 在这里添加执行后的操作
        logger.info("validate_prompt_proxy end...")
        return result

    return wrapper


execution.validate_prompt = validate_prompt_proxy(execution.validate_prompt)


def send_sync_proxy(func):
    def wrapper(*args, **kwargs):
        global need_sync
        global prompt_id
        logger.info(f"send_sync_proxy start... {need_sync},{prompt_id}")
        if not need_sync:
            func(*args, **kwargs)
        elif QUEUE_URL and REGION:
            logger.info(f"send_sync_proxy params... {QUEUE_URL},{REGION},{need_sync},{prompt_id}")
            event = args[1]
            data = args[2]
            sid = args[3] if len(args) == 4 else None
            sqs_client = boto3.client('sqs', region_name=REGION)
            message_body = {'prompt_id': prompt_id, 'event': event, 'data': data, 'sid': sid}
            response = sqs_client.send_message(
                QueueUrl=QUEUE_URL,
                MessageBody=json.dumps(message_body),
                MessageGroupId=prompt_id
            )
            message_id = response['MessageId']
            logger.info(f'send_sync_proxy message_id :{message_id} message_body: {message_body}')
        logger.info(f"send_sync_proxy end...")

    return wrapper


server.PromptServer.send_sync = send_sync_proxy(server.PromptServer.send_sync)
