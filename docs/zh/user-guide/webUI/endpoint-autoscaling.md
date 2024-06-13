# SageMaker 异步端点自动扩展

Amazon SageMaker 提供了能力自动扩展模型推理端点，以响应流量模式的变化。本文档解释了如何为由此解决方案创建的 Amazon SageMaker 异步端点启用自动扩展。

## 概述

所提供的解决方案为 Amazon SageMaker 中的特定端点和变体启用了自动扩展。自动扩展通过两个扩展策略进行管理：

1. **目标跟踪扩展策略**：此策略基于 `CPUUtilization` 指标调整所需的实例计数。其目的是保持CPU利用率在50%。如果平均CPU利用率在5分钟内高于50%，警报将触发应用程序自动扩展以扩展 Sagemaker 端点，直到它达到最大实例数。

   基于CPU利用率的扩展策略是使用 `put_scaling_policy` 方法定义的。它指定了以下参数：
   - `TargetValue`：50% 的 CPU 利用率
   - `ScaleInCooldown`：300秒
   - `ScaleOutCooldown`：300秒

2. **阶梯扩展策略**：此策略允许您根据 `HasBacklogWithoutCapacity` 指标定义扩展调整的步骤。此策略是为了让应用程序自动扩展在有推断请求但端点有0实例时将实例数从0增加到1。

阶梯扩展策略被定义为基于 `HasBacklogWithoutCapacity` 指标调整容量。它包括：
- `AdjustmentType`：ChangeInCapacity
- `MetricAggregationType`：平均
- `Cooldown`：300秒
- `StepAdjustments`：指定基于警报违规大小的扩展调整。

### 以下是 Sagemaker 异步端点自动扩展策略的示例：

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
