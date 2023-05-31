from typing import Dict

import boto3


def publish_msg(topic_arn, msg, subject):
    client = boto3.client('sns')
    client.publish(
        TopicArn=topic_arn,
        Message=str(msg),
        Subject=subject
    )


def get_s3_presign_urls(bucket_name, base_key, filenames) -> Dict[str, str]:
    s3 = boto3.client('s3')
    presign_url_map = {}
    for filename in filenames:
        key = f'{base_key}/{filename}'
        url = s3.generate_presigned_url('put_object',
                                        Params={'Bucket': bucket_name,
                                                'Key': key,
                                                },
                                        ExpiresIn=3600 * 24 * 7)
        presign_url_map[filename] = url

    return presign_url_map
