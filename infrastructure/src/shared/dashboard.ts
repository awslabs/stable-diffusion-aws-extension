import * as cw from 'aws-cdk-lib/aws-cloudwatch';
import {Construct} from "constructs";
import {Aws} from "aws-cdk-lib";

export class DashboardStack {

    constructor(scope: Construct) {
        const last_build_time = new Date().toISOString();
        const period = 300;
        const dashboardBody = {
                "widgets": [
                    {
                        "type": "text",
                        "x": 0,
                        "y": 0,
                        "width": 24,
                        "height": 2,
                        "properties": {
                            "markdown": `## ESD (Extension for Stable Diffusion on AWS) \n Last Build Time: ${last_build_time} \n`
                        }
                    },
                    {
                        "height": 6,
                        "width": 16,
                        "y": 18,
                        "x": 0,
                        "type": "metric",
                        "properties": {
                            "metrics": [
                                [
                                    "ESD",
                                    "EndpointReadySeconds",
                                    "Service",
                                    "Comfy",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "Minimum"
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "Average"
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION
                                    }
                                ]
                            ],
                            "view": "gauge",
                            "stacked": false,
                            "region": Aws.REGION,
                            "period": period,
                            "stat": "Maximum",
                            "title": "Comfy-EndpointReadySeconds",
                            "yAxis": {
                                "left": {
                                    "min": 0,
                                    "max": 100
                                }
                            }
                        }
                    },
                    {
                        "height": 5,
                        "width": 16,
                        "y": 32,
                        "x": 0,
                        "type": "metric",
                        "properties": {
                            "metrics": [
                                [
                                    "ESD",
                                    "EndpointReadySeconds",
                                    "Service",
                                    "Stable-Diffusion",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "Minimum"
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "Average"
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION
                                    }
                                ]
                            ],
                            "sparkline": true,
                            "view": "gauge",
                            "region": Aws.REGION,
                            "title": "SD-EndpointReadySeconds",
                            "period": period,
                            "stat": "Maximum",
                            "yAxis": {
                                "left": {
                                    "min": 0,
                                    "max": 100
                                }
                            }
                        }
                    },
                    {
                        "height": 4,
                        "width": 12,
                        "y": 10,
                        "x": 12,
                        "type": "metric",
                        "properties": {
                            "metrics": [
                                [
                                    "ESD",
                                    "DownloadFileSeconds",
                                    "Service",
                                    "Comfy",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "Minimum"
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "Average"
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION
                                    }
                                ]
                            ],
                            "sparkline": true,
                            "view": "singleValue",
                            "region": Aws.REGION,
                            "period": period,
                            "stat": "Maximum",
                            "title": "Comfy-DownloadFileSeconds"
                        }
                    },
                    {
                        "height": 4,
                        "width": 12,
                        "y": 10,
                        "x": 0,
                        "type": "metric",
                        "properties": {
                            "metrics": [
                                [
                                    "ESD",
                                    "InstanceInitSeconds",
                                    "Service",
                                    "Comfy",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "Minimum"
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "Average"
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION
                                    }
                                ]
                            ],
                            "sparkline": true,
                            "view": "singleValue",
                            "region": Aws.REGION,
                            "period": period,
                            "stat": "Maximum",
                            "title": "Comfy-InstanceInitSeconds"
                        }
                    },
                    {
                        "height": 4,
                        "width": 12,
                        "y": 14,
                        "x": 0,
                        "type": "metric",
                        "properties": {
                            "metrics": [
                                [
                                    "ESD",
                                    "DecompressFileSeconds",
                                    "Service",
                                    "Comfy",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "Minimum"
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "Average"
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION
                                    }
                                ]
                            ],
                            "sparkline": true,
                            "view": "singleValue",
                            "region": Aws.REGION,
                            "title": "Comfy-DecompressFileSeconds",
                            "period": period,
                            "stat": "Maximum"
                        }
                    },
                    {
                        "height": 4,
                        "width": 12,
                        "y": 24,
                        "x": 12,
                        "type": "metric",
                        "properties": {
                            "metrics": [
                                [
                                    "ESD",
                                    "DownloadFileSeconds",
                                    "Service",
                                    "Stable-Diffusion",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "Minimum"
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "Average"
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION
                                    }
                                ]
                            ],
                            "sparkline": true,
                            "view": "singleValue",
                            "region": Aws.REGION,
                            "period": period,
                            "stat": "Maximum",
                            "title": "SD-DownloadFileSeconds"
                        }
                    },
                    {
                        "height": 4,
                        "width": 12,
                        "y": 24,
                        "x": 0,
                        "type": "metric",
                        "properties": {
                            "metrics": [
                                [
                                    "ESD",
                                    "InstanceInitSeconds",
                                    "Service",
                                    "Stable-Diffusion",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "Minimum"
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "Average"
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION
                                    }
                                ]
                            ],
                            "sparkline": true,
                            "view": "singleValue",
                            "region": Aws.REGION,
                            "period": period,
                            "stat": "Maximum",
                            "title": "SD-InstanceInitSeconds"
                        }
                    },
                    {
                        "height": 4,
                        "width": 12,
                        "y": 28,
                        "x": 0,
                        "type": "metric",
                        "properties": {
                            "metrics": [
                                [
                                    "ESD",
                                    "DecompressFileSeconds",
                                    "Service",
                                    "Stable-Diffusion",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "Minimum"
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "Average"
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION
                                    }
                                ]
                            ],
                            "sparkline": true,
                            "view": "singleValue",
                            "region": Aws.REGION,
                            "period": period,
                            "stat": "Maximum",
                            "title": "SD-DecompressFileSeconds"
                        }
                    },
                    {
                        "height": 5,
                        "width": 8,
                        "y": 5,
                        "x": 0,
                        "type": "metric",
                        "properties": {
                            "metrics": [
                                [
                                    "ESD",
                                    "InferenceTotal",
                                    "Service",
                                    "Stable-Diffusion",
                                    {
                                        "region": Aws.REGION
                                    }
                                ],
                                [
                                    ".",
                                    "InferenceSucceed",
                                    ".",
                                    ".",
                                    {
                                        "region": Aws.REGION
                                    }
                                ]
                            ],
                            "sparkline": true,
                            "view": "singleValue",
                            "region": Aws.REGION,
                            "period": period,
                            "stat": "Sum",
                            "title": "SD-Inference",
                            "stacked": false
                        }
                    },
                    {
                        "height": 5,
                        "width": 16,
                        "y": 5,
                        "x": 8,
                        "type": "metric",
                        "properties": {
                            "metrics": [
                                [
                                    "ESD",
                                    "InferenceLatency",
                                    "Service",
                                    "Stable-Diffusion",
                                    {
                                        "region": Aws.REGION
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "p99"
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "Maximum"
                                    }
                                ]
                            ],
                            "sparkline": true,
                            "view": "gauge",
                            "region": Aws.REGION,
                            "period": period,
                            "stat": "Average",
                            "stacked": false,
                            "title": "SD-InferenceLatency",
                            "yAxis": {
                                "left": {
                                    "min": 0,
                                    "max": 100
                                }
                            }
                        }
                    },
                    {
                        "height": 5,
                        "width": 8,
                        "y": 0,
                        "x": 0,
                        "type": "metric",
                        "properties": {
                            "metrics": [
                                [
                                    "ESD",
                                    "InferenceTotal",
                                    "Service",
                                    "Comfy",
                                    {
                                        "region": Aws.REGION
                                    }
                                ],
                                [
                                    ".",
                                    "InferenceSucceed",
                                    ".",
                                    ".",
                                    {
                                        "region": Aws.REGION
                                    }
                                ]
                            ],
                            "sparkline": true,
                            "view": "singleValue",
                            "region": Aws.REGION,
                            "title": "Comfy-Inference",
                            "period": period,
                            "stat": "Sum"
                        }
                    },
                    {
                        "height": 5,
                        "width": 16,
                        "y": 0,
                        "x": 8,
                        "type": "metric",
                        "properties": {
                            "metrics": [
                                [
                                    "ESD",
                                    "InferenceLatency",
                                    "Service",
                                    "Comfy",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "Average"
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "stat": "p99",
                                        "region": Aws.REGION
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION
                                    }
                                ]
                            ],
                            "sparkline": true,
                            "view": "gauge",
                            "region": Aws.REGION,
                            "stat": "Maximum",
                            "period": period,
                            "yAxis": {
                                "left": {
                                    "min": 0,
                                    "max": 10
                                }
                            },
                            "title": "Comfy-InferenceLatency"
                        }
                    },
                    {
                        "height": 4,
                        "width": 12,
                        "y": 28,
                        "x": 12,
                        "type": "metric",
                        "properties": {
                            "metrics": [
                                [
                                    "ESD",
                                    "UploadEndpointCacheSeconds",
                                    "Service",
                                    "Stable-Diffusion",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "Minimum"
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "Maximum"
                                    }
                                ]
                            ],
                            "sparkline": true,
                            "view": "singleValue",
                            "region": Aws.REGION,
                            "period": period,
                            "stat": "Average",
                            "title": "SD-UploadEndpointCacheSeconds"
                        }
                    },
                    {
                        "height": 4,
                        "width": 12,
                        "y": 14,
                        "x": 12,
                        "type": "metric",
                        "properties": {
                            "metrics": [
                                [
                                    "ESD",
                                    "UploadEndpointCacheSeconds",
                                    "Service",
                                    "Comfy",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "Minimum"
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "Maximum"
                                    }
                                ]
                            ],
                            "sparkline": true,
                            "view": "singleValue",
                            "region": Aws.REGION,
                            "title": "Comfy-UploadEndpointCacheSeconds",
                            "period": period,
                            "stat": "Average"
                        }
                    },
                    {
                        "height": 5,
                        "width": 8,
                        "y": 32,
                        "x": 16,
                        "type": "metric",
                        "properties": {
                            "metrics": [
                                [
                                    "ESD",
                                    "DownloadFileSize",
                                    "Service",
                                    "Stable-Diffusion",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "Minimum"
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION
                                    }
                                ]
                            ],
                            "sparkline": true,
                            "view": "singleValue",
                            "region": Aws.REGION,
                            "period": period,
                            "stat": "Maximum",
                            "title": "SD-DownloadFileSize"
                        }
                    },
                    {
                        "height": 4,
                        "width": 24,
                        "y": 37,
                        "x": 0,
                        "type": "metric",
                        "properties": {
                            "metrics": [
                                [
                                    "ESD",
                                    "TrainingLatency",
                                    "Service",
                                    "Stable-diffusion",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "Minimum"
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "Average"
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION
                                    }
                                ]
                            ],
                            "sparkline": true,
                            "view": "singleValue",
                            "region": Aws.REGION,
                            "period": period,
                            "stat": "Maximum",
                            "title": "TrainingLatency"
                        }
                    },
                    {
                        "height": 6,
                        "width": 8,
                        "y": 18,
                        "x": 16,
                        "type": "metric",
                        "properties": {
                            "metrics": [
                                [
                                    "ESD",
                                    "DownloadFileSize",
                                    "Service",
                                    "Comfy",
                                    {
                                        "stat": "Minimum"
                                    }
                                ],
                                [
                                    "..."
                                ]
                            ],
                            "sparkline": true,
                            "view": "singleValue",
                            "region": Aws.REGION,
                            "stat": "Maximum",
                            "period": period,
                            "title": "Comfy-DownloadFileSize"
                        }
                    },
                    {
                        "type": "metric",
                        "x": 0,
                        "y": 0,
                        "width": 24,
                        "height": 5,
                        "properties": {
                            "metrics": [
                                [
                                    "ESD",
                                    "QueueLatency",
                                    "Service",
                                    "Stable-Diffusion",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "Minimum"
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "p99"
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "region": Aws.REGION,
                                        "stat": "Maximum"
                                    }
                                ]
                            ],
                            "view": "gauge",
                            "region": Aws.REGION,
                            "yAxis": {
                                "left": {
                                    "min": 0,
                                    "max": 100
                                }
                            },
                            "period": period,
                            "stat": "Average",
                            "title": "SDQueueLatency"
                        }
                    },
                    {
                        "type": "metric",
                        "x": 0,
                        "y": 5,
                        "width": 24,
                        "height": 5,
                        "properties": {
                            "metrics": [
                                [
                                    "ESD",
                                    "QueueLatency",
                                    "Service",
                                    "Comfy",
                                    {
                                        "stat": "Minimum"
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "stat": "Average"
                                    }
                                ],
                                [
                                    "...",
                                    {
                                        "stat": "p99"
                                    }
                                ],
                                [
                                    "..."
                                ]
                            ],
                            "view": "gauge",
                            "region": Aws.REGION,
                            "yAxis": {
                                "left": {
                                    "min": 0,
                                    "max": 100
                                }
                            },
                            "period": period,
                            "stat": "Maximum",
                            "title": "ComfyQueueLatency"
                        }
                    }
                ]
            }
        ;

        new cw.CfnDashboard(scope, `EsdDashboard`, {
            dashboardName: `ESD`,
            dashboardBody: JSON.stringify(dashboardBody)
        });
    }

}
