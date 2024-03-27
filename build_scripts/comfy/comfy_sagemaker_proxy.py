import datetime
import json
import os
import tarfile

import boto3
import execution
import server
from aiohttp import web
from altair import Key

global sqs_url_using
global need_sync
global prompt_id

REGION = os.environ.get('AWS_REGION')
BUCKET = os.environ.get('BUCKET_NAME')
QUEUE_URL = os.environ.get('QUEUE_URL')
GEN_INSTANCE_ID = os.environ.get('INSTANCE_UNIQUE_ID')
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
        return {"prepare_result": True, "gen_instance_id": GEN_INSTANCE_ID}
    except Exception as e:
        return {"prepare_result": False, "gen_instance_id": GEN_INSTANCE_ID, "error_msg": e}


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
    global need_sync
    # TODO serve 级别加锁
    global prompt_id
    json_data = await request.json()
    print(f"invocations start json_data:{json_data}")

    try:
        print(
            f'bucket_name: {BUCKET}, region: {REGION}, need_sync: {need_sync}')
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


async def check_and_get_last_ddb_sync_record():
    sync_response = sync_table.query(
        KeyConditionExpression=Key('endpoint_name').eq(ENDPOINT_NAME),
        Limit=1,
        ScanIndexForward=False
    )
    latest_sync_record = sync_response['Items'][0] if 'Items' in sync_response and len(sync_response['Items']) > 0 else None
    if latest_sync_record:
        print("sync latest record:", latest_sync_record)
        key_condition_expression = ('endpoint_name = :endpoint_name_val AND gen_instance_id = :gen_instance_id_val '
                                    'AND last_sync_request_id = :last_sync_request_id_val')
        expression_attribute_values = {
            ':endpoint_name_val': ENDPOINT_NAME,
            ':gen_instance_id_val': GEN_INSTANCE_ID,
            ':last_sync_request_id_val': latest_sync_record['last_sync_request_id']
        }
        instance_monitor_response = instance_monitor_table.query(
            KeyConditionExpression=key_condition_expression,
            ExpressionAttributeValues=expression_attribute_values
        )
        items = instance_monitor_response.get('Items', [])

        return True, latest_sync_record
    else:
        print("no sync record fund")
        return False, None


async def get_last_sync_instance_record():
    response = sync_table.query(
        KeyConditionExpression=Key('endpoint_name').eq(ENDPOINT_NAME),
        Limit=1,
        ScanIndexForward=False
    )
    latest_record = response['Items'][0] if 'Items' in response and len(response['Items']) > 0 else None
    if latest_record:
        print("sync latest record:", latest_record)
        return latest_record
    else:
        print("no sync record fund")
        return None


def sync_ddb_instance_monitor():
    response = sync_table.query(
        KeyConditionExpression=Key('endpoint_name').eq(ENDPOINT_NAME),
        Limit=1,
        ScanIndexForward=False
    )
    latest_record = response['Items'][0] if 'Items' in response and len(response['Items']) > 0 else None
    if latest_record:
        print("sync latest record:", latest_record)
        return latest_record
    else:
        print("no sync record fund")


def update_sync_instance_count():
    print(f"Updating DynamoDB {field_name} to {field_value} for: {endpoint_deployment_job_id}")
    # 更新记录
    update_expression = "SET sync_status = :status, endpoint_snapshot = :snapshot"
    expression_attribute_values = {
        ":status": new_sync_status,
        ":snapshot": new_endpoint_snapshot
    }

    sync_table.update_item(
        Key={'endpoint_name': endpoint_name},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_attribute_values
    )
    print("记录更新成功")


@server.PromptServer.instance.routes.post("/sync_instance")
async def sync_instance():
    print(f"sync_instance start ！！ {datetime.datetime.now()}")
    try:

        gen_instance_id = os.environ.get('INSTANCE_UNIQUE_ID')
        endpoint_name = os.environ.get('ENDPOINT_NAME')
        endpoint_id = os.environ.get('ENDPOINT_ID')

        image_url = os.environ.get('IMAGE_URL')
        ecr_image_tag = os.environ.get('ECR_IMAGE_TAG')
        instance_type = os.environ.get('INSTANCE_TYPE')
        created_at = os.environ.get('CREATED_AT')

        # 定时获取ddb的sync记录 并将最新id的写入到环境变量中 比较 如果变更 那么就执行sync逻辑 否则继续轮训
        need_sync, syc_record = check_and_get_last_ddb_sync_record()
        if not syc_record:
            return True
        await prepare_comfy_env(syc_record)
        # update ddb instance and sync count

        return web.Response(status=200)
    except Exception as e:
        print("exception occurred", e)
        return web.Response(status=500)


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