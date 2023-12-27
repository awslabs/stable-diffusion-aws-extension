import json
import logging
import os
from dataclasses import dataclass

import boto3

from common.response import no_content

logger = logging.getLogger('delete_datasets')
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
dataset_info_table = dynamodb.Table(os.environ.get('DATASET_INFO_TABLE'))
dataset_item_table = dynamodb.Table(os.environ.get('DATASET_ITEM_TABLE'))

s3_bucket_name = os.environ.get('S3_BUCKET_NAME')
s3 = boto3.resource('s3')
bucket = s3.Bucket(s3_bucket_name)


@dataclass
class DeleteDatasetsEvent:
    dataset_name_list: [str]


def handler(event, ctx):
    logger.info(f'event: {event}')
    logger.info(f'ctx: {ctx}')

    body = DeleteDatasetsEvent(**json.loads(event['body']))

    # unique list for preventing duplicate delete
    dataset_name_list = list(set(body.dataset_name_list))

    for dataset_name in dataset_name_list:

        # get dataset items
        files = dataset_item_table.query(
            KeyConditionExpression='dataset_name = :dataset_name',
            ExpressionAttributeValues={
                ':dataset_name': dataset_name
            }
        )

        if 'Items' in files:
            logger.info(f"files: {files['Items']}")
            for file in files['Items']:
                dataset_item_table.delete_item(
                    Key={
                        'dataset_name': dataset_name,
                        'sort_key': file['sort_key']
                    }
                )

        prefix = f"dataset/{dataset_name}/"
        logger.info(f'delete prefix: {prefix}')

        response = bucket.objects.filter(Prefix=prefix).delete()
        logger.info(f'delete response: {response}')

        dataset_info_table.delete_item(Key={'dataset_name': dataset_name})

    return no_content(message='datasets deleted')
