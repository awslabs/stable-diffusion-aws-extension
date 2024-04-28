import datetime
import logging
import os

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

cloudwatch = boto3.client('cloudwatch')

download_file_seconds = os.getenv('DOWNLOAD_FILE_SECONDS')
decompress_seconds = os.getenv('DECOMPRESS_SECONDS')


def record_seconds(metric_name, seconds):
    response = cloudwatch.put_metric_data(
        Namespace='ESD',
        MetricData=[
            {
                'MetricName': metric_name,
                'Dimensions': [
                    {
                        'Name': 'Service',
                        'Value': 'Comfy'
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
        record_seconds('DecompressSeconds', decompress_seconds)
