
このソリューションにデプロイ、更新、管理されるリソースをデプロイ、更新、管理する際は、監視対象のアカウントに最小限の権限を付与することをお勧めします。

このソリューションにデプロイ、更新、管理されるリソースをデプロイ、更新、管理するために必要な権限は以下の通りです:

```json 
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                "apigateway:*",
                "application-autoscaling:DeregisterScalableTarget",
                "application-autoscaling:PutScalingPolicy",
                "application-autoscaling:RegisterScalableTarget",
                "cloudformation:*",
                "cloudwatch:DeleteAlarms",
                "cloudwatch:DescribeAlarms",
                "cloudwatch:PutMetricAlarm",
                "cloudwatch:PutMetricData",
                "dynamodb:*",
                "ecr:*",
                "events:*",
                "iam:*",
                "kms:*",
                "lambda:*",
                "logs:*",
                "s3:*",
                "sagemaker:*",
                "sns:*",
                "states:*",
                "sts:AssumeRole"
            ],
            "Resource": "*",
            "Effect": "Allow"
        }
    ]
}
```
