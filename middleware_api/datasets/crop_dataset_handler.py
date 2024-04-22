import json
import logging
import math
import os
from datetime import datetime

import boto3
import numpy as np
from PIL import Image
from aws_lambda_powertools import Tracer

from common.ddb_service.client import DynamoDbUtilsService
from common.util import split_s3_path
from inferences.inference_libs import upload_file_to_s3
from libs.data_types import DatasetItem
from libs.enums import DataStatus
from libs.utils import response_error

tracer = Tracer()
dataset_item_table = os.environ.get('DATASET_ITEM_TABLE')
dataset_info_table = os.environ.get('DATASET_INFO_TABLE')
bucket_name = os.environ.get('S3_BUCKET_NAME')
user_table = os.environ.get('MULTI_USER_TABLE')
crop_lambda_name = os.environ.get('CROP_LAMBDA_NAME')
lambda_client = boto3.client('lambda')
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

ddb_service = DynamoDbUtilsService(logger=logger)
s3_client = boto3.client('s3')


@tracer.capture_lambda_handler
def handler(event, context):
    _filter = {}

    try:
        logger.info(json.dumps(event))

        dataset_name = event['dataset_name']
        user_roles = event['user_roles']

        timestamp = datetime.now().timestamp()
        item = DatasetItem(
            dataset_name=dataset_name,
            sort_key=f'{timestamp}_{f.name}',
            name=f.name,
            type=f.type,
            data_status=DataStatus.Enabled,
            params={},
            allowed_roles_or_users=user_roles
        )

        resize_image(event['src_img_s3_path'], event['max_resolution'])

        # todo insert new dataset item

        return {}

    except Exception as e:
        return response_error(e)


def resize_image(src_img_s3_path, max_resolution="512x512", interpolation='lanczos'):
    # split s3 path
    bucket_name, key_src = split_s3_path(src_img_s3_path)
    key_dst = os.path.dirname(key_src) + '_' + max_resolution + os.path.basename(key_src)
    # download file for src_img_s3_path
    local_src_folder = os.path.join('/tmp', os.path.dirname(key_src))
    local_dst_folder = os.path.join('/tmp', os.path.dirname(key_src) + '_crop')
    os.makedirs(local_src_folder, exist_ok=True)
    os.makedirs(local_dst_folder, exist_ok=True)

    local_src_file_path = os.path.join(local_src_folder, os.path.basename(key_src))
    local_dst_file_path = os.path.join(local_dst_folder, os.path.basename(key_src))

    s3_client.download_file(bucket_name, key_src, local_src_file_path)

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
        # upload the file to the destination s3 path (.txt or .caption or etc.)
        upload_file_to_s3(local_src_file_path, bucket_name, key_dst)
    else:
        # Load image
        image = Image.open(local_src_file_path)
        if not image.mode == "RGB":
            image = image.convert("RGB")

        # Calculate max_pixels from max_resolution string
        width = int(max_resolution.split("x")[0])
        height = int(max_resolution.split("x")[1])

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
        new_img = np.zeros((height, width, 3), dtype=np.uint8)

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
        image.save(local_dst_file_path, quality=100)

        upload_file_to_s3(local_dst_file_path, bucket_name, key_dst)
