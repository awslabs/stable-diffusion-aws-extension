import json
import logging
import os
from typing import Dict
from functools import reduce
import boto3

s3 = boto3.client('s3')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)
sns_client = boto3.client('sns')


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


def generate_presign_url(bucket_name, key, expires=3600, method='put_object') -> Dict[str, str]:
    return s3.generate_presigned_url(method,
                                     Params={'Bucket': bucket_name,
                                             'Key': key,
                                             },
                                     ExpiresIn=expires)


def load_json_from_s3(bucket_name: str, key: str):
    '''
    Get the JSON file from the specified bucket and key
    '''
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


def upload_json_to_s3(bucket_name: str, file_key: str, json_data: dict):
    '''
    Upload the JSON file from the specified bucket and key
    '''
    try:
        s3.put_object(Body=json.dumps(json_data), Bucket=bucket_name, Key=file_key)
        logger.info(f"Dictionary uploaded to S3://{bucket_name}/{file_key}")
    except Exception as e:
        logger.info(f"Error uploading dictionary: {e}")


def split_s3_path(s3_path):
    path_parts = s3_path.replace("s3://", "").split("/")
    bucket = path_parts.pop(0)
    key = "/".join(path_parts)
    return bucket, key
