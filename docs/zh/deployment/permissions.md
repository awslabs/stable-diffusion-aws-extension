部署、更新、以及管理本方案部署的资源所需要的权限如下：

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
