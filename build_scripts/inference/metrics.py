import datetime
import logging
import os
import shutil
import subprocess
import threading
import time

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

endpoint_name = os.getenv('ENDPOINT_NAME', 'test')
endpoint_instance_id = os.getenv('ENDPOINT_INSTANCE_ID', 'default')

if service_type == 'sd':
    service_type = 'Stable-Diffusion'
else:
    service_type = 'Comfy'


def record_size(metric_name, size: float):
    return {
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
    }


def record_seconds(metric_name, seconds):
    return {
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
    }


def get_gpu_utilization():
    try:
        output = subprocess.check_output(['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'])
        gpu_utilization = [int(util.strip()) for util in output.decode('utf-8').split('\n') if util.strip()]
        return gpu_utilization
    except subprocess.CalledProcessError:
        return None


def get_gpu_memory_utilization():
    try:
        output = subprocess.check_output(
            ['nvidia-smi', '--query-gpu=utilization.memory', '--format=csv,noheader,nounits'])
        gpu_memory_utilization = [int(utilization.strip()) for utilization in output.decode('utf-8').split('\n') if
                                  utilization.strip()]
        return gpu_memory_utilization
    except subprocess.CalledProcessError:
        return None


def gpu_metrics():
    data = []
    utilization = get_gpu_utilization()
    if utilization is not None:
        for device_id, util in enumerate(utilization):
            data.append({
                'MetricName': 'GPUUtilization',
                'Dimensions': [
                    {
                        'Name': 'Endpoint',
                        'Value': endpoint_name
                    },
                    {
                        'Name': 'Instance',
                        'Value': endpoint_instance_id
                    },
                    {
                        'Name': 'InstanceGPU',
                        'Value': f"GPU{device_id}"
                    }
                ],
                'Timestamp': datetime.datetime.utcnow(),
                'Value': util,
                'Unit': 'Percent'
            })

    memory_utilization = get_gpu_memory_utilization()
    if memory_utilization is not None:
        for device_id, utilization in enumerate(memory_utilization):
            data.append({
                'MetricName': 'GPUMemoryUtilization',
                'Dimensions': [
                    {
                        'Name': 'Endpoint',
                        'Value': endpoint_name
                    },
                    {
                        'Name': 'Instance',
                        'Value': endpoint_instance_id
                    },
                    {
                        'Name': 'InstanceGPU',
                        'Value': f"GPU{device_id}"
                    }
                ],
                'Timestamp': datetime.datetime.utcnow(),
                'Value': utilization,
                'Unit': 'Percent'
            })

    response = cloudwatch.put_metric_data(
        Namespace='ESD',
        MetricData=data
    )


def get_disk_usage(path):
    total, used, free = shutil.disk_usage(path)
    return {
        "total": total,
        "used": used,
        "free": free,
        "used_percent": used / total * 100
    }


def storage_metrics(path: str, name: str = ''):
    data = []
    disk_usage = get_disk_usage(path)

    disk_usage['total'] = disk_usage['total'] // (2 ** 30)
    disk_usage['used'] = disk_usage['used'] // (2 ** 30)
    disk_usage['free'] = disk_usage['free'] // (2 ** 30)
    disk_usage['used_percent'] = f"{disk_usage['used_percent']:.2f}"

    data.append({
        'MetricName': f'{name}DiskTotal',
        'Dimensions': [
            {
                'Name': 'Endpoint',
                'Value': endpoint_name
            },
            {
                'Name': 'Instance',
                'Value': endpoint_instance_id
            },
        ],
        'Timestamp': datetime.datetime.utcnow(),
        'Value': disk_usage['total'],
        'Unit': 'Gigabytes'
    })

    data.append({
        'MetricName': f'{name}DiskUsed',
        'Dimensions': [
            {
                'Name': 'Endpoint',
                'Value': endpoint_name
            },
            {
                'Name': 'Instance',
                'Value': endpoint_instance_id
            },
        ],
        'Timestamp': datetime.datetime.utcnow(),
        'Value': disk_usage['used'],
        'Unit': 'Gigabytes'
    })

    data.append({
        'MetricName': f'{name}DiskFree',
        'Dimensions': [
            {
                'Name': 'Endpoint',
                'Value': endpoint_name
            },
            {
                'Name': 'Instance',
                'Value': endpoint_instance_id
            },
        ],
        'Timestamp': datetime.datetime.utcnow(),
        'Value': disk_usage['free'],
        'Unit': 'Gigabytes'
    })

    data.append({
        'MetricName': f'{name}DiskPercentage',
        'Dimensions': [
            {
                'Name': 'Endpoint',
                'Value': endpoint_name
            },
            {
                'Name': 'Instance',
                'Value': endpoint_instance_id
            },
        ],
        'Timestamp': datetime.datetime.utcnow(),
        'Value': float(disk_usage['used_percent']),
        'Unit': 'Percent'
    })

    cloudwatch.put_metric_data(
        Namespace='ESD',
        MetricData=data
    )


def monitor_metrics(interval=10):
    while True:
        time.sleep(interval)
        try:
            gpu_metrics()
            storage_metrics('/home/ubuntu')
        except Exception as e:
            logger.error(f"Error in monitoring info: {e}")


if __name__ == "__main__":
    data = []

    if download_file_seconds is not None:
        download_file_seconds = int(download_file_seconds)
        data.append(record_seconds('DownloadFileSeconds', download_file_seconds))

    if decompress_seconds is not None:
        decompress_seconds = int(decompress_seconds)
        data.append(record_seconds('DecompressFileSeconds', decompress_seconds))

    if instance_init_seconds is not None:
        instance_init_seconds = int(instance_init_seconds)
        data.append(record_seconds('InstanceInitSeconds', instance_init_seconds))

    if upload_endpoint_cache_seconds is not None:
        upload_endpoint_cache_seconds = int(upload_endpoint_cache_seconds)
        data.append(record_seconds('UploadEndpointCacheSeconds', upload_endpoint_cache_seconds))

    if download_file_size is not None:
        download_file_size = float(download_file_size)
        data.append(record_size('DownloadFileSize', download_file_size))

    if len(data) > 0:
        response = cloudwatch.put_metric_data(
            Namespace='ESD',
            MetricData=data
        )
        logger.info(f"init record_metric response: {response}")

    metrics_thread = threading.Thread(target=monitor_metrics, args=(10,))
    metrics_thread.start()
