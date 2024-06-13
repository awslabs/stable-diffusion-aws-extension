import json
import logging
import math
import os
from dataclasses import dataclass
from datetime import datetime
from typing import List

import boto3
import numpy as np
from PIL import Image
from aws_lambda_powertools import Tracer

from common.ddb_service.client import DynamoDbUtilsService
from common.util import upload_file_to_s3
from libs.data_types import DatasetItem
from libs.enums import DataStatus
from libs.utils import response_error

tracer = Tracer()
dataset_item_table = os.environ.get('DATASET_ITEM_TABLE')
bucket_name = os.environ.get('S3_BUCKET_NAME')
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)
ddb_service = DynamoDbUtilsService(logger=logger)
s3_client = boto3.client('s3')


@dataclass
class DatasetCropItemEvent:
    dataset_name: str
    prefix: str
    type: str
    max_resolution: str
    name: str
    old_s3_location: str
    user_roles: List[str]


@tracer.capture_lambda_handler
def handler(event, context):
    _filter = {}

    try:
        logger.info(json.dumps(event))

        event_parse = DatasetCropItemEvent(**event)

        resize_image(event_parse)

        timestamp = datetime.now().timestamp()
        item = DatasetItem(
            dataset_name=event_parse.dataset_name,
            sort_key=f'{timestamp}_{event_parse.name}',
            name=event_parse.name,
            type=event_parse.type,
            data_status=DataStatus.Enabled,
            params={},
            allowed_roles_or_users=event_parse.user_roles
        )
        ddb_service.put_items(dataset_item_table, item.__dict__)

        return {}

    except Exception as e:
        return response_error(e)


def resize_image(event: DatasetCropItemEvent, interpolation='lanczos'):
    if event.prefix:
        target_key = f"dataset/{event.dataset_name}/{event.prefix}/{event.name}"
    else:
        target_key = f"dataset/{event.dataset_name}/{event.name}"

    local_src_file_path = f'/tmp/{event.dataset_name}_{event.prefix}_{event.name}'
    local_dst_file_path = f'/tmp/{event.dataset_name}_{event.prefix}_crop_{event.name}'

    s3_client.download_file(bucket_name, event.old_s3_location, local_src_file_path)

    # Select interpolation method
    if interpolation == 'lanczos':
        interpolation_type = Image.LANCZOS
    elif interpolation == 'cubic':
        interpolation_type = Image.BICUBIC
    else:
        interpolation_type = Image.NEAREST

    # Iterate through all files in src_img_folder
    img_exts = (".png", ".jpg", ".jpeg", ".webp", ".bmp")  # copy from train_util.py

    # Check if the image is png, jpg or webp etc...
    if not local_src_file_path.endswith(img_exts):
        upload_file_to_s3(file_name=local_src_file_path, bucket=bucket_name, object_name=target_key)
    else:
        # Load image
        image = Image.open(local_src_file_path)
        # save the original image mode, such as RGBA -> RGBA
        # if not image.mode == "RGB":
        #     image = image.convert("RGB")

        # Calculate max_pixels from max_resolution string
        width = int(event.max_resolution.split("x")[0])
        height = int(event.max_resolution.split("x")[1])

        # Calculate current number of pixels
        current_height = image.size[1]
        current_width = image.size[0]

        # Check if the image needs resizing
        if current_width > width and current_height > height:
            # Calculate scaling factor
            scale_factor_width = width / current_width
            scale_factor_height = height / current_height

            if scale_factor_height > scale_factor_width:
                new_width = math.ceil(current_width * scale_factor_height)
                image = image.resize((new_width, height), interpolation_type)
            elif scale_factor_height < scale_factor_width:
                new_height = math.ceil(current_height * scale_factor_width)
                image = image.resize((width, new_height), interpolation_type)
            else:
                image = image.resize((width, height), interpolation_type)

        resized_img = np.array(image)
        channel_val = resized_img.shape[2]
        new_img = np.zeros((height, width, channel_val), dtype=np.uint8)

        # Center crop the image to the calculated dimensions
        new_y = 0
        new_x = 0
        height_dst = height
        width_dst = width
        y = int((resized_img.shape[0] - height) / 2)
        if y < 0:
            new_y = -y
            height_dst = resized_img.shape[0]
            y = 0
        x = int((resized_img.shape[1] - width) / 2)
        if x < 0:
            new_x = -x
            width_dst = resized_img.shape[1]
            x = 0
        new_img[new_y:new_y + height_dst, new_x:new_x + width_dst] = resized_img[y:y + height_dst, x:x + width_dst]

        # Save resized image in dst_img_folder
        image = Image.fromarray(new_img)
        image.save(local_dst_file_path, quality=95)

        upload_file_to_s3(file_name=local_dst_file_path, bucket=bucket_name, object_name=target_key)
