import json
import logging
import os

import boto3
from aws_lambda_powertools import Tracer

from common.ddb_service.client import DynamoDbUtilsService

aws_region = os.environ.get('AWS_REGION')

cloudwatch = boto3.client('cloudwatch')
logs = boto3.client('logs')
lambda_client = boto3.client('lambda')
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.INFO)
tracer = Tracer()
sagemaker_endpoint_table = os.environ.get('ENDPOINT_TABLE_NAME')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

sagemaker = boto3.client('sagemaker')
ddb_service = DynamoDbUtilsService(logger=logger)
esd_version = os.environ.get("ESD_VERSION")


# lambda: handle sagemaker events
@tracer.capture_lambda_handler
def handler(event, context):
    logger.info(json.dumps(event))

    eps = list_sagemaker_endpoints()
    for ep in eps:
        create_ds(ep['EndpointName'])

    return {}


def ds(ep_name: str):
    dashboard_body = {
        "widgets": [
            {
                "type": "text",
                "x": 0,
                "y": 0,
                "width": 24,
                "height": 1,
                "properties": {
                    "markdown": f"## Endpoint Dashboard - {ep_name}"
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
                            "InferenceCount",
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
                    "period": 86400
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
                    "period": 900,
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
                    "period": 900,
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
                    "view": "singleValue",
                    "region": aws_region,
                    "title": "GPUUtilization",
                    "period": 3600,
                    "yAxis": {
                        "left": {
                            "min": 0,
                            "max": 100
                        }
                    },
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
                    "view": "singleValue",
                    "region": aws_region,
                    "title": "CPUUtilization",
                    "period": 3600,
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
                    "period": 300,
                    "yAxis": {
                        "left": {
                            "min": 1,
                            "max": 100
                        }
                    }
                }
            },
        ]
    }

    gpus_ds = resolve_gpu_ds(ep_name)
    for gpu_ds in gpus_ds:
        dashboard_body['widgets'].append(gpu_ds)

    return json.dumps(dashboard_body)


def resolve_gpu_ds(ep_name: str):
    list = []

    # Call the function with the custom namespace you want to list metrics from
    custom_metrics = list_custom_metrics('ESD')

    ids = []
    # Print or process the metrics
    for metric in custom_metrics:
        if metric['MetricName'] == 'InferenceCount':
            if len(metric['Dimensions']) == 3:
                for dm in metric['Dimensions']:
                    if dm['Name'] == 'Endpoint' and dm['Value'] == ep_name:
                        instance_id = metric['Dimensions'][1]['Value']
                        gpu_number = metric['Dimensions'][2]['Value']

                        ids.append({"instance_id": instance_id, "gpu_number": gpu_number,
                                    "index": f"{instance_id}-{gpu_number}"})

    sorted_ids = sorted(ids, key=lambda x: x['index'], reverse=True)

    x = 0
    y = 10
    i = 0
    for item in sorted_ids:
        list.append({
            "height": 7,
            "width": 6,
            "y": y,
            "x": x,
            "type": "metric",
            "properties": {
                "metrics": [
                    [
                        "ESD",
                        "InferenceCount",
                        "Endpoint",
                        ep_name,
                        "Instance",
                        item['instance_id'],
                        "InstanceGPU",
                        item['gpu_number'],
                        {
                            "region": aws_region
                        }
                    ]
                ],
                "sparkline": True,
                "view": "singleValue",
                "stacked": True,
                "region": aws_region,
                "stat": "Sum",
                "period": 900,
                "title": f"{item['index']}-Tasks"
            }
        })
        i = i + 1
        x = x + 6
        if i >= 4:
            i = 0
            x = 0
            y = y + 1

    return list


def delete_dashboard(ep_name: str):
    cloudwatch.delete_dashboards(
        DashboardNames=[ep_name]
    )
    print(f"Dashboard {ep_name} deleted")


def get_dashboard(dashboard_name):
    try:
        response = cloudwatch.get_dashboard(DashboardName=dashboard_name)
        return response['DashboardBody']
    except cloudwatch.exceptions.ResourceNotFound:
        return None


def create_ds(ep_name: str):
    # Check if the dashboard exists
    existing_dashboard = get_dashboard(ep_name)

    if existing_dashboard:
        # Update the existing dashboard
        cloudwatch.put_dashboard(DashboardName=ep_name, DashboardBody=ds(ep_name))
        print(f"Dashboard '{ep_name}' updated successfully.")
    else:
        # Create a new dashboard
        cloudwatch.put_dashboard(DashboardName=ep_name, DashboardBody=ds(ep_name))
        print(f"Dashboard '{ep_name}' created successfully.")


def list_custom_metrics(namespace):
    # Use the list_metrics function to retrieve metrics from the specified namespace
    response = cloudwatch.list_metrics(
        Namespace=namespace
    )

    # Extract and return the list of metrics from the response
    return response['Metrics']


def list_sagemaker_endpoints():
    response = sagemaker.list_endpoints()
    return response['Endpoints']
