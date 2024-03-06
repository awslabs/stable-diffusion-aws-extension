When deploying, updating, and managing the resources deployed in this solution, it is recommended to follow the minimum permission principle to grant permissions to the monitored account.

The permissions required for deploying, updating, and managing the resources deployed in this solution are as follows:

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
