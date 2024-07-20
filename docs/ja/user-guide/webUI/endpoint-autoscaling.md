
# SageMaker 非同期エンドポイントの自動スケーリング

Amazon SageMaker では、トラフィックパターンの変化に応じて、モデルの推論エンドポイントを自動的にスケーリングする機能が提供されています。このドキュメントでは、このソリューションで作成された Amazon SageMaker 非同期エンドポイントの自動スケーリングの設定について説明します。

## 概要

このソリューションは、Amazon SageMaker の特定のエンドポイントとバリアントに対して自動スケーリングを有効にします。自動スケーリングは、2つのスケーリングポリシーによって管理されます。

1. **ターゲットトラッキングスケーリングポリシー**: このポリシーは、`CPUUtilization` メトリックに基づいて、必要なインスタンス数を調整します。CPU の使用率を 50% に維持することを目標としています。CPU の平均使用率が5分間 50% を超えた場合、アラームがトリガーされ、最大インスタンス数に達するまで SageMaker エンドポイントのスケールアウトが行われます。

CPU の使用率に基づくスケーリングポリシーは、`put_scaling_policy` メソッドを使って定義されます。以下のパラメータが指定されています:
- `TargetValue`: 50% CPU の使用率
- `ScaleInCooldown`: 300 秒
- `ScaleOutCooldown`: 300 秒

2. **ステップスケーリングポリシー**: このポリシーは、`HasBacklogWithoutCapacity` メトリックに基づいて、スケーリング調整のためのステップを定義できます。このポリシーは、推論リクエストがあるがエンドポイントが0インスタンスの場合、インスタンス数を0から1に増やすために作成されています。

ステップスケーリングポリシーは、`HasBacklogWithoutCapacity` メトリックに基づいてキャパシティを調整するように定義されています。以下の項目が含まれます:
- `AdjustmentType`: ChangeInCapacity 
- `MetricAggregationType`: Average 
- `Cooldown`: 300 秒
- `StepAdjustments`: アラームの大きさに基づいたスケーリング調整を指定しています。

### 以下は、SageMaker 非同期エンドポイントの自動スケーリングポリシーの例です:

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

