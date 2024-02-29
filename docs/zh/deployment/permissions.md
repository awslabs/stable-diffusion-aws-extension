部署、更新、以及管理本方案部署的资源时，建议遵循最小权限原则为受监控帐户授予权限。

如需提前指定 IAM 角色以部署 CloudFormation 模板，请按如下步骤操作：

1. [打开 IAM 控制台](https://console.aws.amazon.com/iam/) 并选择 **角色**, 然后点击 **创建角色**。
2. 在**可信实体类型**中选择 **亚马逊云科技服务**，在下面**服务或使用案例**列表中, 选择 **CloudFormation**。
3. 点击 **下一步**，并输入角色名称，点击 **创建角色**
4. 在创建好后回到角色列表中打开该角色，选择 **添加权限**，然后点击 **创建内联策略**，点击 **JSON** 切换到JSON编辑器并将如下JSON内容完整复制到 **策略编辑器** 中，点击下一步。
5. 点击 **创建策略** 完成。之后在部署 CloudFormation 模板的时候就可以在 **权限** 部分选择该IAM角色进行部署了。


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
