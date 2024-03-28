import datetime
import json
import os
import tarfile

import boto3
import execution
import server
from aiohttp import web
from altair import Key

global need_sync
global prompt_id

REGION = os.environ.get('AWS_REGION')
BUCKET = os.environ.get('BUCKET_NAME')
QUEUE_URL = os.environ.get('QUEUE_URL')
GEN_INSTANCE_ID = os.environ.get('ENDPOINT_INSTANCE_ID')
ENDPOINT_NAME = os.environ.get('ENDPOINT_NAME')
ENDPOINT_ID = os.environ.get('ENDPOINT_ID')

INSTANCE_MONITOR_TABLE_NAME = os.environ.get('INSTANCE_MONITOR_TABLE')
SYNC_TABLE_NAME = os.environ.get('SYNC_TABLE')

dynamodb = boto3.resource('dynamodb', region_name=REGION)
sync_table = dynamodb.Table(SYNC_TABLE_NAME)
instance_monitor_table = dynamodb.Table(INSTANCE_MONITOR_TABLE_NAME)


async def prepare_comfy_env(sync_item: dict):
    try:
        print(f"prepare_environment start sync_item:{sync_item}")
        prepare_type = sync_item['prepare_type']
        if prepare_type in ['default', 'models']:
            sync_s3_files_or_folders_to_local('models', '/opt/ml/code/models', False)
        if prepare_type in ['default', 'inputs']:
            sync_s3_files_or_folders_to_local('input', '/opt/ml/code/input', False)
        if prepare_type in ['default', 'nodes']:
            sync_s3_files_or_folders_to_local('nodes', '/opt/ml/code/custom_nodes', True)
        if prepare_type == 'custom':
            sync_source_path = sync_item['s3_source_path']
            local_target_path = sync_item['local_target_path']
            if not sync_source_path or not local_target_path:
                print("s3_source_path and local_target_path should not be empty")
            else:
                sync_s3_files_or_folders_to_local(sync_source_path,
                                                  f'/opt/ml/code/{local_target_path}', False)
        elif prepare_type == 'other':
            sync_script = sync_item['sync_script']
            print("sync_script")
            # sync_script.startswith('s5cmd') 不允许
            if sync_script and (sync_script.startswith("pip install") or sync_script.startswith("apt-get")
                                or sync_script.startswith("os.environ")):
                os.system(sync_script)

        need_reboot = sync_item['need_reboot']
        if need_reboot and need_reboot.lower() == 'true':
            os.environ['NEED_REBOOT'] = 'true'
        else:
            os.environ['NEED_REBOOT'] = 'false'
        print("prepare_environment end")
        os.environ['last_sync_request_id'] = sync_item['request_id']
        return True
    except Exception as e:
        return False


# def create_tar_gz(source_file, target_tar_gz):
#     # Example usage:
#     # source_file_path = "/path/to/your/source/file.txt"
#     # target_tar_gz_path = "/path/to/your/target/file.tar.gz"
#     with tarfile.open(target_tar_gz, "w:gz") as tar:
#         tar.add(source_file, arcname=os.path.basename(source_file))


def sync_s3_files_or_folders_to_local(s3_path, local_path, need_un_tar):
    print("sync_s3_models_or_inputs_to_local start")
    # s5cmd_command = f'/opt/ml/code/tools/s5cmd cp "s3://{bucket_name}/{s3_path}/*" "{local_path}/"'
    s5cmd_command = f'/opt/ml/code/tools/s5cmd sync "s3://{BUCKET}/{s3_path}/" "{local_path}/"'
    try:
        # TODO 注意添加去重逻辑
        # TODO 注意记录更新信息 避免冲突或者环境改坏被误会
        print(s5cmd_command)
        os.system(s5cmd_command)
        print(f'Files copied from "s3://{BUCKET}/{s3_path}/*" to "{local_path}/"')
        if need_un_tar:
            for filename in os.listdir(local_path):
                if filename.endswith(".tar.gz"):
                    tar_filepath = os.path.join(local_path, filename)
                    with tarfile.open(tar_filepath, "r:gz") as tar:
                        tar.extractall(path=local_path)
                    os.remove(tar_filepath)
                    print(f'File {tar_filepath} extracted and removed')
    except Exception as e:
        print(f"Error executing s5cmd command: {e}")


def sync_local_outputs_to_s3(s3_path, local_path):
    print("sync_local_outputs_to_s3 start")
    s5cmd_command = f'/opt/ml/code/tools/s5cmd cp "{local_path}/*" "s3://{BUCKET}/{s3_path}/" '
    try:
        print(s5cmd_command)
        os.system(s5cmd_command)
        print(f'Files copied local to "s3://{BUCKET}/{s3_path}/" to "{local_path}/"')
    except Exception as e:
        print(f"Error executing s5cmd command: {e}")


@server.PromptServer.instance.routes.post("/invocations")
async def invocations(request):
    # TODO serve 级别加锁
    json_data = await request.json()
    print(f"invocations start json_data:{json_data}")
    global need_sync
    need_sync = json_data["need_sync"]
    global prompt_id
    prompt_id = json_data["prompt_id"]
    try:
        print(
            f'bucket_name: {BUCKET}, region: {REGION}')
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
            print("the environment is not ready valid[0] is false, need to resync")
            return web.Response(status=500, text="the environment is not ready valid[0] is false")
        extra_data = {}
        if "extra_data" in json_data:
            extra_data = json_data["extra_data"]
        if "client_id" in json_data:
            extra_data["client_id"] = json_data["client_id"]
        if valid[0]:
            prompt_id = json_data['prompt_id']
            e = execution.PromptExecutor(server_instance)
            outputs_to_execute = valid[2]
            e.execute(json_data['prompt'], prompt_id, extra_data, outputs_to_execute)
            # TODO 看下是否需要 调整为利用 sg 的 output path
            sync_local_outputs_to_s3(f'output/{prompt_id}', '/opt/ml/code/output')
            clean_cmd = 'rm -rf /opt/ml/code/output'
            os.system(clean_cmd)
        # TODO 回写instance id 同步的放在body中 异步的放在s3的path中
        # GEN_INSTANCE_ID

        return web.Response(status=200)
    except Exception as e:
        print("exception occurred", e)
        return web.Response(status=500)


def get_last_ddb_sync_record():
    sync_response = sync_table.query(
        KeyConditionExpression=Key('endpoint_name').eq(ENDPOINT_NAME),
        Limit=1,
        ScanIndexForward=False
    )
    latest_sync_record = sync_response['Items'][0] if ('Items' in sync_response
                                                       and len(sync_response['Items']) > 0) else None
    if latest_sync_record:
        print(f"latest_sync_record is：{latest_sync_record}")
        return latest_sync_record

    print("no latest_sync_record found")
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
        print(f"instance_monitor_record is {instance_monitor_record}")
        return instance_monitor_record

    print("no instance_monitor_record found")
    return None


def save_sync_instance_count(last_sync_request_id: str, sync_status: str):
    gen_instance_id = os.environ.get('ENDPOINT_INSTANCE_ID')
    endpoint_name = os.environ.get('ENDPOINT_NAME')
    endpoint_id = os.environ.get('ENDPOINT_ID')

    item = {
        'endpoint_id': endpoint_id,
        'endpoint_name': endpoint_name,
        'gen_instance_id': gen_instance_id,
        'sync_status': sync_status,
        'last_sync_request_id': last_sync_request_id,
        'last_sync_time': str(datetime.datetime.now()),
        'sync_list': [],
        'create_time': str(datetime.datetime.now()),
        'last_heartbeat_time': str(datetime.datetime.now())
    }
    save_resp = instance_monitor_table.put_item(Item=item)
    print(f"save instance item {save_resp}")
    return save_resp


def update_sync_instance_monitor(instance_monitor_record):
    # 更新记录
    update_expression = ("SET sync_status = : new_sync_status, last_sync_request_id = :sync_request_id, "
                         "sync_list = :sync_list, last_sync_time = :sync_time, last_heartbeat_time = :heartbeat_time")
    expression_attribute_values = {
        ":new_sync_status": instance_monitor_record['sync_status'],
        ":sync_request_id": instance_monitor_record['last_sync_request_id'],
        ":sync_list": instance_monitor_record['sync_list'],
        ":sync_time": str(datetime.datetime.now()),
        ":heartbeat_time": str(datetime.datetime.now()),
    }

    response = sync_table.update_item(
        Key={'endpoint_name': instance_monitor_record['endpoint_name'],
             'gen_instance_id': instance_monitor_record['gen_instance_id']},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_attribute_values
    )
    print(f"update_sync_instance_monitor :{response}")
    return response


@server.PromptServer.instance.routes.post("/sync_instance")
async def sync_instance():
    print(f"sync_instance start ！！ {datetime.datetime.now()}")
    try:
        last_sync_record = get_last_ddb_sync_record()
        if not last_sync_record:
            print("no last sync record found do not need sync")
            return True

        if ('request_id' in last_sync_record and last_sync_record['request_id']
                and os.environ.get('last_sync_request_id')
                and os.environ.get('last_sync_request_id') == last_sync_record['request_id']):
            print("last sync record already sync by os check")
            return True

        instance_monitor_record = get_latest_ddb_instance_monitor_record()
        if not instance_monitor_record:
            sync_already = await prepare_comfy_env(last_sync_record)
            print("should init prepare instance_monitor_record")
            sync_status = 'success' if sync_already else 'failed'
            save_sync_instance_count(last_sync_record['request_id'], sync_status)
        else:
            if ('last_sync_request_id' in instance_monitor_record and instance_monitor_record['last_sync_request_id']
                    and instance_monitor_record['last_sync_request_id'] == last_sync_record['request_id']):
                print("last sync record already sync")
                return True

            sync_already = await prepare_comfy_env(last_sync_record)
            instance_monitor_record['sync_status'] = 'success' if sync_already else 'failed'
            instance_monitor_record['last_sync_request_id'] = last_sync_record['request_id']
            sync_list = instance_monitor_record['sync_list'] if 'sync_list' in instance_monitor_record and instance_monitor_record['sync_list'] else []
            sync_list.append(last_sync_record['request_id'])

            instance_monitor_record['sync_list'] = sync_list
            print("should update prepare instance_monitor_record")
            update_sync_instance_monitor(instance_monitor_record)
        return True
    except Exception as e:
        print("exception occurred", e)
        return False


def validate_prompt_proxy(func):
    def wrapper(*args, **kwargs):
        # 在这里添加您的代理逻辑
        print("validate_prompt_proxy start...")
        # 调用原始函数
        result = func(*args, **kwargs)
        # 在这里添加执行后的操作
        print("validate_prompt_proxy end...")
        return result

    return wrapper


execution.validate_prompt = validate_prompt_proxy(execution.validate_prompt)


def send_sync_proxy(func):
    def wrapper(*args, **kwargs):
        global need_sync
        global prompt_id
        print(f"send_sync_proxy start... {need_sync},{prompt_id}")
        if not need_sync:
            func(*args, **kwargs)
        elif QUEUE_URL and REGION:
            print(f"send_sync_proxy params... {QUEUE_URL},{REGION},{need_sync},{prompt_id}")
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
            print(f'send_sync_proxy message_id :{message_id} message_body: {message_body}')
        print(f"send_sync_proxy end...")

    return wrapper


server.PromptServer.send_sync = send_sync_proxy(server.PromptServer.send_sync)
