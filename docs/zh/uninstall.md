!!! Warning "警告"
    卸载该解决方案前，请手动删除由此堆栈创建的Amazon SageMaker Endpoint资源，具体步骤参考**用户指南--主标签页**中的[删除已部署推理节点](./user-guide/CloudAssetsManage.md)。卸载此堆栈，将同时删除由此堆栈创建的AWS Lambda相关函数，指示模型训练、微调和推理日志和映射关系的DynamoDB表，和AWS Step Functions等。


要卸载Stable Diffusion亚马逊云科技插件解决方案，请删除CloudFormation堆栈。

您可以使用亚马逊云科技管理控制台或CLI删除CloudFormation堆栈。

## 使用亚马逊云科技管理控制台删除堆栈

1. 登录AWS CloudFormation控制台。
2. 在**堆栈**页面上，选择此方案的安装堆栈。
3. 选择**删除**。



## 使用CLI删除堆栈

1. 确定命令行在您的环境中是否可用。有关安装说明，请参阅CLI用户指南中的[CLI是什么](https://docs.aws.amazon.com/zh_cn/cli/latest/userguide/cli-chap-welcome.html){:target="_blank"}。
2. 确认CLI可用后，请运行以下命令:
```
bash aws cloudformation delete-stack --stack-name <installation-stack-name>
```

