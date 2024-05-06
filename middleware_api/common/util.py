import base64
import datetime
import enum
import json
import logging
import os
from functools import reduce
from io import BytesIO
from typing import Dict

import boto3
import numpy
from PIL import Image, PngImagePlugin
from aws_lambda_powertools import Tracer

from libs.comfy_data_types import InferenceResult
from libs.utils import log_json

tracer = Tracer()
s3 = boto3.client('s3')
s3_resource = boto3.resource('s3')
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)
sns_client = boto3.client('sns')
s3_client = boto3.client('s3')
bucket_name = os.environ.get('S3_BUCKET_NAME')
s3_bucket = s3_resource.Bucket(bucket_name)

cloudwatch = boto3.client('cloudwatch')

endpoint_name = os.getenv('ENDPOINT_NAME')
endpoint_instance_id = os.getenv('ENDPOINT_INSTANCE_ID')


def record_ep_metrics(ep_name: str):
    response = cloudwatch.put_metric_data(
        Namespace='ESD',
        MetricData=[
            {
                'MetricName': 'InferenceCount',
                'Dimensions': [
                    {
                        'Name': 'Endpoint',
                        'Value': ep_name
                    },
                ],
                'Timestamp': datetime.datetime.utcnow(),
                'Value': 1,
                'Unit': 'Count'
            },
        ]
    )
    logger.info(f"record_metric response: {response}")


def record_count_metrics(metric_name='InferenceSucceed', service='Stable-Diffusion'):
    response = cloudwatch.put_metric_data(
        Namespace='ESD',
        MetricData=[
            {
                'MetricName': metric_name,
                'Dimensions': [
                    {
                        'Name': 'Service',
                        'Value': service
                    },
                ],
                'Timestamp': datetime.datetime.utcnow(),
                'Value': 1,
                'Unit': 'Count'
            },
        ]
    )
    logger.info(f"record_metric response: {response}")


def record_seconds_metrics(start_time: str, metric_name='Inference', service='Stable-Diffusion'):
    start_time = datetime.datetime.fromisoformat(start_time)
    latency = (datetime.datetime.now() - start_time).seconds

    response = cloudwatch.put_metric_data(
        Namespace='ESD',
        MetricData=[
            {
                'MetricName': metric_name,
                'Dimensions': [
                    {
                        'Name': 'Service',
                        'Value': service
                    },
                ],
                'Timestamp': datetime.datetime.utcnow(),
                'Value': latency,
                'Unit': 'Seconds'
            },
        ]
    )
    logger.info(f"record_metric response: {response}")


def record_latency_metrics(start_time, metric_name='Inference', service='Stable-Diffusion'):
    start_time = datetime.datetime.fromisoformat(start_time)
    latency = (datetime.datetime.now() - start_time).microseconds

    response = cloudwatch.put_metric_data(
        Namespace='ESD',
        MetricData=[
            {
                'MetricName': metric_name,
                'Dimensions': [
                    {
                        'Name': 'Service',
                        'Value': service
                    },
                ],
                'Timestamp': datetime.datetime.utcnow(),
                'Value': latency,
                'Unit': 'Microseconds'
            },
        ]
    )
    logger.info(f"record_metric response: {response}")


def get_multi_query_params(event, param_name: str, default=None):
    value = default
    if 'multiValueQueryStringParameters' in event:
        multi_query = event['multiValueQueryStringParameters']
        if multi_query and param_name in multi_query and len(multi_query[param_name]) > 0:
            value = multi_query[param_name]

    return value


def get_query_param(event, param_name: str, default=None):
    if 'queryStringParameters' in event:
        queries = event['queryStringParameters']
        if queries and param_name in queries:
            return queries[param_name]

    return default


def resolve_instance_invocations_num(instance_type: str, service_type: str):
    if service_type == "sd":
        return 1

    if instance_type == 'ml.g5.12xlarge':
        return 4

    if instance_type == 'ml.p4d.24xlarge':
        return 8

    return 1


def query_data(data, paths):
    value = data
    for path in paths:
        value = value.get(path)
        if not value:
            path_string = reduce(lambda x, y: f"{x}.{y}", paths)
            raise ValueError(f"Missing {path_string}")

    return value


def publish_msg(topic_arn, msg, subject):
    sns_client.publish(
        TopicArn=topic_arn,
        Message=str(msg),
        Subject=subject
    )


def get_s3_presign_urls(bucket_name, base_key, filenames) -> Dict[str, str]:
    return _get_s3_presign_urls(bucket_name, base_key, filenames, expires=3600 * 24 * 7, method='put_object')


def get_s3_get_presign_urls(bucket_name, base_key, filenames) -> Dict[str, str]:
    return _get_s3_presign_urls(bucket_name, base_key, filenames, expires=3600 * 24, method='get_object')


def _get_s3_presign_urls(bucket_name, base_key, filenames, expires=3600, method='put_object') -> Dict[str, str]:
    presign_url_map = {}
    for filename in filenames:
        key = f'{base_key}/{filename}'
        url = s3.generate_presigned_url(method,
                                        Params={'Bucket': bucket_name,
                                                'Key': key,
                                                },
                                        ExpiresIn=expires)
        presign_url_map[filename] = url

    return presign_url_map


@tracer.capture_method
def generate_presign_url(bucket_name, key, expires=3600, method='put_object') -> Dict[str, str]:
    return s3.generate_presigned_url(method,
                                     Params={'Bucket': bucket_name,
                                             'Key': key,
                                             },
                                     ExpiresIn=expires)


@tracer.capture_method
def load_json_from_s3(key: str):
    key = key.replace(f"s3://{bucket_name}/", '')
    response = s3.get_object(Bucket=bucket_name, Key=key)
    json_file = response['Body'].read().decode('utf-8')
    data = json.loads(json_file)

    return data


def save_json_to_file(json_string: str, folder_path: str, file_name: str):
    os.makedirs(folder_path, exist_ok=True)
    file_path = os.path.join(folder_path, file_name)

    with open(file_path, 'w') as file:
        file.write(json.dumps(json_string))

    return file_path


def get_pil_metadata(pil_image):
    # Copy any text-only metadata
    metadata = PngImagePlugin.PngInfo()
    for key, value in pil_image.info.items():
        if isinstance(key, str) and isinstance(value, str):
            metadata.add_text(key, value)

    return metadata


def encode_pil_to_base64(pil_image):
    with BytesIO() as output_bytes:
        pil_image.save(output_bytes, "PNG", pnginfo=get_pil_metadata(pil_image))
        bytes_data = output_bytes.getvalue()

    base64_str = str(base64.b64encode(bytes_data), "utf-8")
    return "data:image/png;base64," + base64_str


def encode_no_json(obj):
    if isinstance(obj, numpy.ndarray):
        return encode_pil_to_base64(Image.fromarray(obj))
    elif isinstance(obj, Image.Image):
        return encode_pil_to_base64(obj)
    elif isinstance(obj, enum.Enum):
        return obj.value
    elif hasattr(obj, '__dict__'):
        return obj.__dict__
    else:
        logger.debug(f'may not able to json dumps {type(obj)}: {str(obj)}')
        return str(obj)


@tracer.capture_method
def upload_json_to_s3(file_key: str, json_data: dict):
    try:
        file_key = file_key.replace(f"s3://{bucket_name}/", '')
        s3.put_object(Body=json.dumps(json_data, indent=4, default=encode_no_json), Bucket=bucket_name, Key=file_key)
        logger.info(f"Dictionary uploaded to s3://{bucket_name}/{file_key}")
    except Exception as e:
        logger.info(f"Error uploading dictionary: {e}")


@tracer.capture_method
def upload_file_to_s3(file_name, bucket, directory=None, object_name=None):
    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file_name

    # Add the directory to the object_name
    if directory:
        object_name = f"{directory}/{object_name}"

    # Upload the file
    try:
        s3_client.upload_file(file_name, bucket, object_name)
        log_json(f"File {file_name} uploaded to {bucket}/{object_name}")
    except Exception as e:
        print(f"Error occurred while uploading {file_name} to {bucket}/{object_name}: {e}")
        return False
    return True


def split_s3_path(s3_path):
    path_parts = s3_path.replace("s3://", "").split("/")
    bucket = path_parts.pop(0)
    key = "/".join(path_parts)
    return bucket, key


@tracer.capture_method
def s3_scan_files(job: InferenceResult):
    job.output_files = s3_scan_files_in_patch(job.output_path)
    job.temp_files = s3_scan_files_in_patch(job.temp_path)

    return job


@tracer.capture_method
def s3_scan_files_in_patch(patch: str):
    files = []
    prefix = patch.replace(f"s3://{bucket_name}/", '')
    for obj in s3_bucket.objects.filter(Prefix=prefix):
        file = obj.key.replace(prefix, '')
        if file:
            files.append(file)

    return files


def generate_presigned_url_for_key(key, expiration=3600):
    key = key.replace(f"s3://{bucket_name}/", '')

    return s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket_name, 'Key': key},
        ExpiresIn=expiration
    )


@tracer.capture_method
def generate_presigned_url_for_keys(prefix, keys, expiration=3600):
    prefix = prefix.replace(f"s3://{bucket_name}/", '')
    new_list = []
    for key in keys:
        new_list.append(generate_presigned_url_for_key(f"{prefix}{key}", expiration))

    return new_list


@tracer.capture_method
def generate_presigned_url_for_job(job):
    if 'output_path' in job and 'output_files' in job:
        job['output_files'] = generate_presigned_url_for_keys(job['output_path'], job['output_files'])

    if 'temp_path' in job and 'temp_files' in job:
        job['temp_files'] = generate_presigned_url_for_keys(job['temp_path'], job['temp_files'])

    return job
