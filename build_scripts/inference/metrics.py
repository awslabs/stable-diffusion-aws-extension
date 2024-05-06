import datetime
import logging
import os

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

cloudwatch = boto3.client('cloudwatch')

service_type = os.getenv('SERVICE_TYPE')
download_file_seconds = os.getenv('DOWNLOAD_FILE_SECONDS')
decompress_seconds = os.getenv('DECOMPRESS_SECONDS')
instance_init_seconds = os.getenv('INSTANCE_INIT_SECONDS')
upload_endpoint_cache_seconds = os.getenv('UPLOAD_ENDPOINT_CACHE_SECONDS')
download_file_size = os.getenv('DOWNLOAD_FILE_SIZE')

if service_type == 'sd':
    service_type = 'Stable-Diffusion'
else:
    service_type = 'Comfy'


def record_size(metric_name, size: float):
    response = cloudwatch.put_metric_data(
        Namespace='ESD',
        MetricData=[
            {
                'MetricName': metric_name,
                'Dimensions': [
                    {
                        'Name': 'Service',
                        'Value': service_type
                    },

                ],
                'Timestamp': datetime.datetime.utcnow(),
                'Value': size,
                'Unit': 'Megabytes'
            },
        ]
    )
    logger.info(f"record_metric response: {response}")


def record_seconds(metric_name, seconds):
    response = cloudwatch.put_metric_data(
        Namespace='ESD',
        MetricData=[
            {
                'MetricName': metric_name,
                'Dimensions': [
                    {
                        'Name': 'Service',
                        'Value': service_type
                    },

                ],
                'Timestamp': datetime.datetime.utcnow(),
                'Value': seconds,
                'Unit': 'Seconds'
            },
        ]
    )
    logger.info(f"record_metric response: {response}")


if __name__ == "__main__":
    if download_file_seconds is not None:
        download_file_seconds = int(download_file_seconds)
        record_seconds('DownloadFileSeconds', download_file_seconds)

    if decompress_seconds is not None:
        decompress_seconds = int(decompress_seconds)
        record_seconds('DecompressFileSeconds', decompress_seconds)

    if instance_init_seconds is not None:
        instance_init_seconds = int(instance_init_seconds)
        record_seconds('InstanceInitSeconds', instance_init_seconds)

    if upload_endpoint_cache_seconds is not None:
        upload_endpoint_cache_seconds = int(upload_endpoint_cache_seconds)
        record_seconds('UploadEndpointCacheSeconds', upload_endpoint_cache_seconds)

    if download_file_size is not None:
        download_file_size = float(download_file_size)
        record_size('DownloadFileSize', download_file_size)
