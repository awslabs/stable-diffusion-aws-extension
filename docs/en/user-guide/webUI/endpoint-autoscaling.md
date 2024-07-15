# SageMaker Async Endpoint Autoscaling

Amazon SageMaker provides capabilities to automatically scale model inference endpoints in response to the changes in traffic patterns. This document explains how autoscaling is enabled for an Amazon SageMaker async endpoint created by this Solution

## Overview

The solution provided enables autoscaling for a specific endpoint and variant in Amazon SageMaker. Autoscaling is managed through two scaling policies:

1. **Target Tracking Scaling Policy**: This policy adjusts the desired instance count based on the `CPUUtilization` metric. It aims to keep the CPU utilization at 50%. If the average CPU utilization is above 50 for 5 minutes, the alarm will trigger application autoscaling to scale out Sagemaker endpoint until it reach the maximum number of instances.
 
   The scaling policy based on CPU utilization is defined using the `put_scaling_policy` method. It specifies the following parameters:
    - `TargetValue`: 50% CPU utilization
    - `ScaleInCooldown`: 300 seconds
    - `ScaleOutCooldown`: 300 seconds

2. **Step Scaling Policy**: This policy allows you to define steps for scaling adjustments based on the `HasBacklogWithoutCapacity` metric. This policy is created to let application autoscaling increase the instance number from 0 to 1 when there is inference request but endpoint has 0 instance.

The step scaling policy is defined to adjust the capacity based on the `HasBacklogWithoutCapacity` metric. It includes:
- `AdjustmentType`: ChangeInCapacity
- `MetricAggregationType`: Average
- `Cooldown`: 300 seconds
- `StepAdjustments`: Specifies the scaling adjustments based on the size of the alarm breach.

### Example of Sagemaker async endpoint autoscaling policy below:

```json
{
    "ScalingPolicies": [
        {
            "PolicyARN": "Your PolicyARN",
            "PolicyName": "HasBacklogWithoutCapacity-ScalingPolicy",
            "ServiceNamespace": "sagemaker",
            "ResourceId": "endpoint/esd-type-c356f91/variant/prod",
            "ScalableDimension": "sagemaker:variant:DesiredInstanceCount",
            "PolicyType": "StepScaling",
            "StepScalingPolicyConfiguration": {
                "AdjustmentType": "ChangeInCapacity",
                "StepAdjustments": [
                    {
                        "MetricIntervalLowerBound": 0.0,
                        "ScalingAdjustment": 1
                    }
                ],
                "Cooldown": 300,
                "MetricAggregationType": "Average"
            },
            "Alarms": [
                {
                    "AlarmName": "stable-diffusion-hasbacklogwithoutcapacity-alarm",
                    "AlarmARN": "Your AlarmARN"
                }
            ],
            "CreationTime": "2023-08-14T13:53:10.480000+08:00"
        },
        {
            "PolicyARN": "Your PolicyARN",
            "PolicyName": "CPUUtil-ScalingPolicy",
            "ServiceNamespace": "sagemaker",
            "ResourceId": "endpoint/esd-type-c356f91/variant/prod",
            "ScalableDimension": "sagemaker:variant:DesiredInstanceCount",
            "PolicyType": "TargetTrackingScaling",
            "TargetTrackingScalingPolicyConfiguration": {
                "TargetValue": 50.0,
                "CustomizedMetricSpecification": {
                    "MetricName": "CPUUtilization",
                    "Namespace": "/aws/sagemaker/Endpoints",
                    "Dimensions": [
                        {
                            "Name": "EndpointName",
                            "Value": "esd-type-c356f91"
                        },
                        {
                            "Name": "VariantName",
                            "Value": "prod"
                        }
                    ],
                    "Statistic": "Average",
                    "Unit": "Percent"
                },
                "ScaleOutCooldown": 300,
                "ScaleInCooldown": 300
            },
            "Alarms": [
                {
                    "AlarmName": "TargetTracking-endpoint/esd-type-c356f91/variant/prod-AlarmHigh-c915b303-9048-40b2-99a7-f5b7e49ab7c4",
                    "AlarmARN": "Your AlarmARN"
                },
                {
                    "AlarmName": "TargetTracking-endpoint/esd-type-c356f91/variant/prod-AlarmLow-2fd61f99-c2e5-4ac6-9722-54030c3f0216",
                    "AlarmARN": "Your AlarmARN"
                }
            ],
            "CreationTime": "2023-08-14T13:53:10.182000+08:00"
        }
    ]
}
```

