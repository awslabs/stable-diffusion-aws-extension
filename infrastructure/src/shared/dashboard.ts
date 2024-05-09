import * as cw from 'aws-cdk-lib/aws-cloudwatch';
import { Construct } from 'constructs';
import { Aws } from 'aws-cdk-lib';

export class DashboardStack {

    constructor(scope: Construct) {
        const last_build_time = new Date().toISOString();
        const region = Aws.REGION;
        const dashboardBody = {
                'widgets': [
                    {
                        'height': 2,
                        'width': 24,
                        'y': 0,
                        'x': 0,
                        'type': 'text',
                        'properties': {
                            'markdown': `## ESD (Extension for Stable Diffusion on AWS) \n Last Build Time: ${last_build_time}`,
                        },
                    },
                    {
                        'height': 5,
                        'width': 16,
                        'y': 26,
                        'x': 0,
                        'type': 'metric',
                        'properties': {
                            'metrics': [
                                [
                                    'ESD',
                                    'EndpointReadySeconds',
                                    'Service',
                                    'Comfy',
                                    {
                                        'region': region,
                                        'stat': 'Minimum',
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                        'stat': 'Average',
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                    },
                                ],
                            ],
                            'stacked': false,
                            'region': region,
                            'period': 300,
                            'stat': 'Maximum',
                            'title': 'Comfy-EndpointReadySeconds',
                            'view': 'gauge',
                            'yAxis': {
                                'left': {
                                    'min': 0,
                                    'max': 100,
                                },
                            },
                        },
                    },
                    {
                        'height': 5,
                        'width': 16,
                        'y': 39,
                        'x': 0,
                        'type': 'metric',
                        'properties': {
                            'metrics': [
                                [
                                    'ESD',
                                    'EndpointReadySeconds',
                                    'Service',
                                    'Stable-Diffusion',
                                    {
                                        'region': region,
                                        'stat': 'Minimum',
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                        'stat': 'Average',
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                    },
                                ],
                            ],
                            'sparkline': true,
                            'view': 'gauge',
                            'region': region,
                            'title': 'SD-EndpointReadySeconds',
                            'period': 300,
                            'stat': 'Maximum',
                            'yAxis': {
                                'left': {
                                    'min': 0,
                                    'max': 100,
                                },
                            },
                        },
                    },
                    {
                        'height': 4,
                        'width': 12,
                        'y': 18,
                        'x': 12,
                        'type': 'metric',
                        'properties': {
                            'metrics': [
                                [
                                    'ESD',
                                    'DownloadFileSeconds',
                                    'Service',
                                    'Comfy',
                                    {
                                        'region': region,
                                        'stat': 'Minimum',
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                        'stat': 'Average',
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                    },
                                ],
                            ],
                            'sparkline': true,
                            'view': 'singleValue',
                            'region': region,
                            'period': 300,
                            'stat': 'Maximum',
                            'title': 'Comfy-DownloadFileSeconds',
                        },
                    },
                    {
                        'height': 4,
                        'width': 12,
                        'y': 18,
                        'x': 0,
                        'type': 'metric',
                        'properties': {
                            'metrics': [
                                [
                                    'ESD',
                                    'InstanceInitSeconds',
                                    'Service',
                                    'Comfy',
                                    {
                                        'region': region,
                                        'stat': 'Minimum',
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                        'stat': 'Average',
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                    },
                                ],
                            ],
                            'sparkline': true,
                            'view': 'singleValue',
                            'region': region,
                            'period': 300,
                            'stat': 'Maximum',
                            'title': 'Comfy-InstanceInitSeconds',
                        },
                    },
                    {
                        'height': 4,
                        'width': 12,
                        'y': 22,
                        'x': 0,
                        'type': 'metric',
                        'properties': {
                            'metrics': [
                                [
                                    'ESD',
                                    'DecompressFileSeconds',
                                    'Service',
                                    'Comfy',
                                    {
                                        'region': region,
                                        'stat': 'Minimum',
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                        'stat': 'Average',
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                    },
                                ],
                            ],
                            'sparkline': true,
                            'view': 'singleValue',
                            'region': region,
                            'title': 'Comfy-DecompressFileSeconds',
                            'period': 300,
                            'stat': 'Maximum',
                        },
                    },
                    {
                        'height': 4,
                        'width': 12,
                        'y': 31,
                        'x': 12,
                        'type': 'metric',
                        'properties': {
                            'metrics': [
                                [
                                    'ESD',
                                    'DownloadFileSeconds',
                                    'Service',
                                    'Stable-Diffusion',
                                    {
                                        'region': region,
                                        'stat': 'Minimum',
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                        'stat': 'Average',
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                    },
                                ],
                            ],
                            'sparkline': true,
                            'view': 'singleValue',
                            'region': region,
                            'period': 300,
                            'stat': 'Maximum',
                            'title': 'SD-DownloadFileSeconds',
                        },
                    },
                    {
                        'height': 4,
                        'width': 12,
                        'y': 31,
                        'x': 0,
                        'type': 'metric',
                        'properties': {
                            'metrics': [
                                [
                                    'ESD',
                                    'InstanceInitSeconds',
                                    'Service',
                                    'Stable-Diffusion',
                                    {
                                        'region': region,
                                        'stat': 'Minimum',
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                        'stat': 'Average',
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                    },
                                ],
                            ],
                            'sparkline': true,
                            'view': 'singleValue',
                            'region': region,
                            'period': 300,
                            'stat': 'Maximum',
                            'title': 'SD-InstanceInitSeconds',
                        },
                    },
                    {
                        'height': 4,
                        'width': 12,
                        'y': 35,
                        'x': 0,
                        'type': 'metric',
                        'properties': {
                            'metrics': [
                                [
                                    'ESD',
                                    'DecompressFileSeconds',
                                    'Service',
                                    'Stable-Diffusion',
                                    {
                                        'region': region,
                                        'stat': 'Minimum',
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                        'stat': 'Average',
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                    },
                                ],
                            ],
                            'sparkline': true,
                            'view': 'singleValue',
                            'region': region,
                            'period': 300,
                            'stat': 'Maximum',
                            'title': 'SD-DecompressFileSeconds',
                        },
                    },
                    {
                        'height': 4,
                        'width': 9,
                        'y': 10,
                        'x': 0,
                        'type': 'metric',
                        'properties': {
                            'metrics': [
                                [
                                    'ESD',
                                    'InferenceTotal',
                                    'Service',
                                    'Stable-Diffusion',
                                    {
                                        'region': region,
                                    },
                                ],
                                [
                                    '.',
                                    'InferenceEndpointReceived',
                                    '.',
                                    '.',
                                ],
                                [
                                    '.',
                                    'InferenceSucceed',
                                    '.',
                                    '.',
                                    {
                                        'region': region,
                                    },
                                ],
                            ],
                            'sparkline': true,
                            'view': 'singleValue',
                            'region': region,
                            'period': 300,
                            'stat': 'Sum',
                            'title': 'SD-Inference',
                            'stacked': false,
                        },
                    },
                    {
                        'height': 4,
                        'width': 15,
                        'y': 10,
                        'x': 9,
                        'type': 'metric',
                        'properties': {
                            'metrics': [
                                [
                                    'ESD',
                                    'InferenceLatency',
                                    'Service',
                                    'Stable-Diffusion',
                                    {
                                        'region': region,
                                        'stat': 'Minimum',
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                        'stat': 'p99',
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                        'stat': 'Maximum',
                                    },
                                ],
                            ],
                            'sparkline': true,
                            'view': 'singleValue',
                            'region': region,
                            'period': 300,
                            'stat': 'Average',
                            'stacked': false,
                            'title': 'SD-InferenceLatency',
                        },
                    },
                    {
                        'height': 4,
                        'width': 9,
                        'y': 2,
                        'x': 0,
                        'type': 'metric',
                        'properties': {
                            'metrics': [
                                [
                                    'ESD',
                                    'InferenceTotal',
                                    'Service',
                                    'Comfy',
                                    {
                                        'region': region,
                                    },
                                ],
                                [
                                    '.',
                                    'InferenceEndpointReceived',
                                    '.',
                                    '.',
                                ],
                                [
                                    '.',
                                    'InferenceSucceed',
                                    '.',
                                    '.',
                                    {
                                        'region': region,
                                    },
                                ],
                            ],
                            'sparkline': true,
                            'view': 'singleValue',
                            'region': region,
                            'title': 'Comfy-Inference',
                            'period': 300,
                            'stat': 'Sum',
                        },
                    },
                    {
                        'height': 4,
                        'width': 15,
                        'y': 2,
                        'x': 9,
                        'type': 'metric',
                        'properties': {
                            'metrics': [
                                [
                                    'ESD',
                                    'InferenceLatency',
                                    'Service',
                                    'Comfy',
                                    {
                                        'region': region,
                                        'stat': 'Minimum',
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'stat': 'p99',
                                        'region': region,
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                        'stat': 'Maximum',
                                    },
                                ],
                            ],
                            'sparkline': true,
                            'view': 'singleValue',
                            'region': region,
                            'stat': 'Average',
                            'period': 300,
                            'title': 'Comfy-InferenceLatency',
                        },
                    },
                    {
                        'height': 4,
                        'width': 12,
                        'y': 35,
                        'x': 12,
                        'type': 'metric',
                        'properties': {
                            'metrics': [
                                [
                                    'ESD',
                                    'UploadEndpointCacheSeconds',
                                    'Service',
                                    'Stable-Diffusion',
                                    {
                                        'region': region,
                                        'stat': 'Minimum',
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                        'stat': 'Maximum',
                                    },
                                ],
                            ],
                            'sparkline': true,
                            'view': 'singleValue',
                            'region': region,
                            'period': 300,
                            'stat': 'Average',
                            'title': 'SD-UploadEndpointCacheSeconds',
                        },
                    },
                    {
                        'height': 4,
                        'width': 12,
                        'y': 22,
                        'x': 12,
                        'type': 'metric',
                        'properties': {
                            'metrics': [
                                [
                                    'ESD',
                                    'UploadEndpointCacheSeconds',
                                    'Service',
                                    'Comfy',
                                    {
                                        'region': region,
                                        'stat': 'Minimum',
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                        'stat': 'Maximum',
                                    },
                                ],
                            ],
                            'sparkline': true,
                            'view': 'singleValue',
                            'region': region,
                            'title': 'Comfy-UploadEndpointCacheSeconds',
                            'period': 300,
                            'stat': 'Average',
                        },
                    },
                    {
                        'height': 5,
                        'width': 8,
                        'y': 39,
                        'x': 16,
                        'type': 'metric',
                        'properties': {
                            'metrics': [
                                [
                                    'ESD',
                                    'DownloadFileSize',
                                    'Service',
                                    'Stable-Diffusion',
                                    {
                                        'region': region,
                                        'stat': 'Minimum',
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                    },
                                ],
                            ],
                            'sparkline': true,
                            'view': 'singleValue',
                            'region': region,
                            'period': 300,
                            'stat': 'Maximum',
                            'title': 'SD-DownloadFileSize',
                        },
                    },
                    {
                        'height': 4,
                        'width': 24,
                        'y': 44,
                        'x': 0,
                        'type': 'metric',
                        'properties': {
                            'metrics': [
                                [
                                    'ESD',
                                    'TrainingLatency',
                                    'Service',
                                    'Stable-Diffusion',
                                    {
                                        'region': region,
                                        'stat': 'Minimum',
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'stat': 'p99',
                                        'region': region,
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                        'stat': 'Maximum',
                                    },
                                ],
                            ],
                            'sparkline': true,
                            'view': 'singleValue',
                            'region': region,
                            'period': 900,
                            'stat': 'Average',
                            'title': 'TrainingLatency',
                        },
                    },
                    {
                        'height': 5,
                        'width': 8,
                        'y': 26,
                        'x': 16,
                        'type': 'metric',
                        'properties': {
                            'metrics': [
                                [
                                    'ESD',
                                    'DownloadFileSize',
                                    'Service',
                                    'Comfy',
                                    {
                                        'stat': 'Minimum',
                                    },
                                ],
                                [
                                    '...',
                                ],
                            ],
                            'sparkline': true,
                            'view': 'singleValue',
                            'region': region,
                            'stat': 'Maximum',
                            'period': 300,
                            'title': 'Comfy-DownloadFileSize',
                        },
                    },
                    {
                        'height': 4,
                        'width': 24,
                        'y': 14,
                        'x': 0,
                        'type': 'metric',
                        'properties': {
                            'metrics': [
                                [
                                    'ESD',
                                    'QueueLatency',
                                    'Service',
                                    'Stable-Diffusion',
                                    {
                                        'region': region,
                                        'stat': 'Minimum',
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                        'stat': 'p99',
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'region': region,
                                        'stat': 'Maximum',
                                    },
                                ],
                            ],
                            'view': 'singleValue',
                            'region': region,
                            'period': 300,
                            'stat': 'Average',
                            'title': 'SDQueueLatency',
                        },
                    },
                    {
                        'height': 4,
                        'width': 24,
                        'y': 6,
                        'x': 0,
                        'type': 'metric',
                        'properties': {
                            'metrics': [
                                [
                                    'ESD',
                                    'QueueLatency',
                                    'Service',
                                    'Comfy',
                                    {
                                        'stat': 'Minimum',
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'stat': 'Average',
                                    },
                                ],
                                [
                                    '...',
                                    {
                                        'stat': 'p99',
                                    },
                                ],
                                [
                                    '...',
                                ],
                            ],
                            'view': 'singleValue',
                            'region': region,
                            'period': 300,
                            'stat': 'Maximum',
                            'title': 'ComfyQueueLatency',
                        },
                    },
                ],
            }

        ;

        new cw.CfnDashboard(scope, `EsdDashboard`, {
            dashboardName: `ESD`,
            dashboardBody: JSON.stringify(dashboardBody),
        });
    }

}
