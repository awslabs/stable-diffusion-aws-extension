import datetime
import json
import logging
import os

import boto3
from aws_lambda_powertools import Tracer

from common.ddb_service.client import DynamoDbUtilsService
from delete_endpoints import get_endpoint_in_sagemaker
from libs.utils import get_endpoint_by_name

aws_region = os.environ.get('AWS_REGION')
esd_version = os.environ.get("ESD_VERSION")
sagemaker_endpoint_table = os.environ.get('ENDPOINT_TABLE_NAME')
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.INFO)

tracer = Tracer()

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)
cloudwatch = boto3.client('cloudwatch')
sagemaker = boto3.client('sagemaker')
ddb_service = DynamoDbUtilsService(logger=logger)
period = 300


@tracer.capture_lambda_handler
def handler(event, context):
    logger.info(json.dumps(event))

    if 'detail' in event and 'EndpointStatus' in event['detail']:
        endpoint_name = event['detail']['EndpointName']
        endpoint_status = event['detail']['EndpointStatus']
        if endpoint_status == 'InService':
            create_ds(endpoint_name)
            clean_ds()
            return {}

    eps = ddb_service.scan(sagemaker_endpoint_table)
    logger.info(f"Endpoints: {eps}")

    for ep in eps:
        ep_name = ep['endpoint_name']['S']
        ep_status = ep['endpoint_status']['S']

        if ep_status == 'Creating':
            continue

        endpoint = get_endpoint_in_sagemaker(ep_name)
        if endpoint is None:
            continue

        create_ds(ep_name)

    clean_ds()
    return {}


def clean_ds():
    ds = cloudwatch.list_dashboards()
    if 'DashboardEntries' in ds:
        prefix = ('comfy-async-', 'comfy-real-time-', 'sd-async-', 'sd-real-time-')
        filtered_dashboards = [dashboard['DashboardName'] for dashboard in ds['DashboardEntries'] if
                               dashboard['DashboardName'].startswith(prefix)]
        for ep_name in filtered_dashboards:
            try:
                get_endpoint_by_name(ep_name)
            except Exception as e:
                print(f"Error: {e}")
                print(f"Deleting {ep_name}")
                cloudwatch.delete_dashboards(DashboardNames=[ep_name])


def ds_body(ep_name: str, custom_metrics):
    last_build_time = datetime.datetime.now().isoformat()
    dashboard_body = {
        "widgets": [
            {
                "type": "text",
                "x": 0,
                "y": 0,
                "width": 24,
                "height": 2,
                "properties": {
                    "markdown": f"## ESD - {ep_name} \n Last Build Time: {last_build_time}"
                }
            },
            {
                "type": "metric",
                "x": 0,
                "y": 0,
                "width": 24,
                "height": 4,
                "properties": {
                    "metrics": [
                        [
                            "ESD",
                            "QueueLatency",
                            "Endpoint",
                            ep_name,
                            {
                                "stat": "Minimum",
                                "region": aws_region
                            }
                        ],
                        [
                            "...",
                            {
                                "stat": "Average",
                                "region": aws_region
                            }
                        ],
                        [
                            "...",
                            {
                                "stat": "p99",
                                "region": aws_region
                            }
                        ],
                        [
                            "...",
                            {
                                "region": aws_region
                            }
                        ]
                    ],
                    "view": "singleValue",
                    "region": aws_region,
                    "period": period,
                    "stat": "Maximum",
                    "title": "QueueLatency"
                }
            },
            {
                "height": 4,
                "width": 6,
                "y": 1,
                "x": 0,
                "type": "metric",
                "properties": {
                    "metrics": [
                        [
                            "ESD",
                            "InferenceEndpointReceived",
                            "Endpoint",
                            ep_name,
                            {
                                "region": aws_region
                            }
                        ],
                        [
                            ".",
                            "InferenceSucceed",
                            ".",
                            ".",
                            {
                                "region": aws_region
                            }
                        ]
                    ],
                    "sparkline": True,
                    "view": "singleValue",
                    "region": aws_region,
                    "title": "Inference Results",
                    "period": period,
                    "stat": "Sum"
                }
            },
            {
                "height": 4,
                "width": 18,
                "y": 1,
                "x": 8,
                "type": "metric",
                "properties": {
                    "metrics": [
                        [
                            "ESD",
                            "InferenceLatency",
                            "Endpoint",
                            ep_name,
                            {
                                "region": aws_region,
                                "stat": "Minimum"
                            }
                        ],
                        [
                            "...",
                            {
                                "region": aws_region
                            }
                        ],
                        [
                            "...",
                            {
                                "stat": "p99",
                                "region": aws_region
                            }
                        ],
                        [
                            "...",
                            {
                                "stat": "Maximum",
                                "region": aws_region
                            }
                        ]
                    ],
                    "sparkline": True,
                    "view": "singleValue",
                    "region": aws_region,
                    "stat": "Average",
                    "period": period,
                    "title": "InferenceLatency"
                }
            },
            {
                "height": 5,
                "width": 6,
                "y": 0,
                "x": 0,
                "type": "metric",
                "properties": {
                    "metrics": [
                        [
                            "ESD",
                            "InferenceTotal",
                            "Endpoint",
                            ep_name,
                            {
                                "region": aws_region
                            }
                        ]
                    ],
                    "sparkline": True,
                    "view": "singleValue",
                    "region": aws_region,
                    "title": "Endpoint Inference",
                    "stat": "Sum",
                    "period": period
                }
            },
            {
                "height": 5,
                "width": 7,
                "y": 0,
                "x": 13,
                "type": "metric",
                "properties": {
                    "metrics": [
                        [
                            "/aws/sagemaker/Endpoints",
                            "MemoryUtilization",
                            "EndpointName",
                            ep_name,
                            "VariantName",
                            "prod",
                            {
                                "region": aws_region,
                                "stat": "Minimum"
                            }
                        ],
                        [
                            "...",
                            {
                                "region": aws_region
                            }
                        ]
                    ],
                    "sparkline": True,
                    "view": "gauge",
                    "region": aws_region,
                    "title": "MemoryUtilization",
                    "period": period,
                    "yAxis": {
                        "left": {
                            "min": 1,
                            "max": 100
                        }
                    },
                    "stat": "Maximum"
                }
            },
            {
                "height": 5,
                "width": 7,
                "y": 0,
                "x": 6,
                "type": "metric",
                "properties": {
                    "metrics": [
                        [
                            "/aws/sagemaker/Endpoints",
                            "GPUMemoryUtilization",
                            "EndpointName",
                            ep_name,
                            "VariantName",
                            "prod",
                            {
                                "region": aws_region,
                                "stat": "Minimum"
                            }
                        ],
                        [
                            "...",
                            {
                                "region": aws_region
                            }
                        ]
                    ],
                    "view": "gauge",
                    "stacked": True,
                    "region": aws_region,
                    "title": "\t GPUMemoryUtilization",
                    "period": period,
                    "yAxis": {
                        "left": {
                            "min": 1,
                            "max": 100
                        }
                    },
                    "stat": "Maximum"
                }
            },
            {
                "height": 5,
                "width": 12,
                "y": 5,
                "x": 0,
                "type": "metric",
                "properties": {
                    "metrics": [
                        [
                            "/aws/sagemaker/Endpoints",
                            "GPUUtilization",
                            "EndpointName",
                            ep_name,
                            "VariantName",
                            "prod",
                            {
                                "region": aws_region,
                                "stat": "Minimum"
                            }
                        ],
                        [
                            "...",
                            {
                                "region": aws_region
                            }
                        ],
                        [
                            "...",
                            {
                                "region": aws_region,
                                "stat": "Maximum"
                            }
                        ]
                    ],
                    "sparkline": True,
                    "view": "gauge",
                    "yAxis": {
                        "left": {
                            "min": 0,
                            "max": 100
                        }
                    },
                    "region": aws_region,
                    "title": "GPUUtilization",
                    "period": period,
                    "stacked": False,
                    "stat": "Average"
                }
            },
            {
                "height": 5,
                "width": 12,
                "y": 5,
                "x": 12,
                "type": "metric",
                "properties": {
                    "metrics": [
                        [
                            "/aws/sagemaker/Endpoints",
                            "CPUUtilization",
                            "EndpointName",
                            ep_name,
                            "VariantName",
                            "prod",
                            {
                                "region": aws_region,
                                "stat": "Minimum"
                            }
                        ],
                        [
                            "...",
                            {
                                "region": aws_region
                            }
                        ],
                        [
                            "...",
                            {
                                "region": aws_region,
                                "stat": "Maximum"
                            }
                        ]
                    ],
                    "sparkline": True,
                    "view": "gauge",
                    "yAxis": {
                        "left": {
                            "min": 0,
                            "max": 100
                        }
                    },
                    "region": aws_region,
                    "title": "CPUUtilization",
                    "period": period,
                    "stat": "Average"
                }
            },
            {
                "height": 5,
                "width": 4,
                "y": 0,
                "x": 20,
                "type": "metric",
                "properties": {
                    "metrics": [
                        [
                            "/aws/sagemaker/Endpoints",
                            "DiskUtilization",
                            "EndpointName",
                            ep_name,
                            "VariantName",
                            "prod",
                            {
                                "region": aws_region
                            }
                        ]
                    ],
                    "view": "singleValue",
                    "stacked": True,
                    "region": aws_region,
                    "title": "DiskUtilization",
                    "period": period,
                }
            },
        ]
    }

    gpus_ds = resolve_gpu_ds(ep_name, custom_metrics)
    for gpu_ds in gpus_ds:
        dashboard_body['widgets'].append(gpu_ds)

    return json.dumps(dashboard_body)


def resolve_gpu_ds(ep_name: str, custom_metrics):
    list = []
    ids = []

    cur_instance_id = None
    for metric in custom_metrics:
        if metric['MetricName'] == 'InferenceTotal':
            if len(metric['Dimensions']) == 3:
                for dm in metric['Dimensions']:
                    if dm['Name'] == 'Endpoint' and dm['Value'] == ep_name:
                        instance_id = metric['Dimensions'][1]['Value']
                        gpu_id = metric['Dimensions'][2]['Value']

                        ids.append({
                            "instance_id": instance_id,
                            "gpu_id": gpu_id,
                            "view": "singleValue",
                            "stat": "Sum",
                            "metric": "InferenceTotal"})

                        ids.append({
                            "instance_id": instance_id,
                            "gpu_id": gpu_id,
                            "view": "singleValue",
                            "stat": "Average",
                            "metric": "GPUUtilization"})

                        ids.append({
                            "instance_id": instance_id,
                            "gpu_id": gpu_id,
                            "view": "singleValue",
                            "stat": "Maximum",
                            "metric": "GPUUtilization"})

                        ids.append({
                            "instance_id": instance_id,
                            "gpu_id": gpu_id,
                            "view": "singleValue",
                            "stat": "Maximum",
                            "metric": "GPUMemoryUtilization"})

    def custom_sort(obj):
        return (-int(obj['instance_id']), obj['gpu_id'])

    ids = sorted(ids, key=custom_sort)

    x = 0
    y = 10

    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f"]
    color_index = 0

    for item in ids:
        if cur_instance_id != item['instance_id']:
            cur_instance_id = item['instance_id']
            list.append({
                "type": "text",
                "x": 0,
                "y": y,
                "width": 24,
                "height": 1,
                "properties": {
                    "background": "transparent",
                    "markdown": f""
                }
            })
            list.append({
                "type": "text",
                "x": 0,
                "y": y,
                "width": 24,
                "height": 1,
                "properties": {
                    "background": "transparent",
                    "markdown": f"# Endpoint Instance - {item['instance_id']}"
                }
            })
            y = y + 2

        list.append({
            "height": 4,
            "width": 6,
            "y": y,
            "x": x,
            "type": "metric",
            "properties": {
                "metrics": [
                    [
                        "ESD",
                        item['metric'],
                        "Endpoint",
                        ep_name,
                        "Instance",
                        item['instance_id'],
                        "InstanceGPU",
                        item['gpu_id'],
                        {
                            "region": aws_region,
                            "label": f"{item['metric']} - {item['stat']}",
                            "color": colors[color_index]
                        }
                    ]
                ],
                "sparkline": True,
                "view": item['view'],
                "yAxis": {
                    "left": {
                        "min": 1,
                        "max": 100
                    }
                },
                "stacked": True,
                "region": aws_region,
                "stat": item['stat'],
                "period": period,
                "title": f"{item['gpu_id']}"
            }
        })

        x = x + 6
        if x >= 24:

            color_index = color_index + 1
            if color_index >= len(colors):
                color_index = 0

            x = 0
            y = y + 1

    logger.info(f"Metrics List:")
    logger.info(json.dumps(list))

    return list


def get_dashboard(dashboard_name):
    try:
        response = cloudwatch.get_dashboard(DashboardName=dashboard_name)
        return response['DashboardBody']
    except cloudwatch.exceptions.ResourceNotFound:
        return None


def create_ds(ep_name: str):
    dimensions = [
        {
            'Name': 'Endpoint',
            'Value': ep_name
        }
    ]

    metrics1 = cloudwatch.list_metrics(Namespace='ESD', MetricName='GPUMemoryUtilization', Dimensions=dimensions)[
        'Metrics']
    metrics2 = cloudwatch.list_metrics(Namespace='ESD', MetricName='GPUUtilization', Dimensions=dimensions)['Metrics']
    metrics3 = cloudwatch.list_metrics(Namespace='ESD', MetricName='InferenceTotal', Dimensions=dimensions)['Metrics']

    custom_metrics = metrics1 + metrics2 + metrics3

    logger.info(f"Custom Metrics: ")
    logger.info(json.dumps(custom_metrics))

    existing_dashboard = get_dashboard(ep_name)

    cloudwatch.put_dashboard(DashboardName=ep_name, DashboardBody=ds_body(ep_name, custom_metrics))

    if existing_dashboard:
        logger.info(f"Dashboard '{ep_name}' updated successfully.")
    else:
        logger.info(f"Dashboard '{ep_name}' created successfully.")
