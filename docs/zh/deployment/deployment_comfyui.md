在部署解决方案之前，建议您先查看本指南中有关架构图和区域支持等信息。然后按照下面的说明配置解决方案并将其部署到您的帐户中。

部署时间：约 20 分钟

## 前提条件


## 部署概述
在亚马逊云科技上部署本解决方案（ComfyUI部分）主要包括以下过程：

- 步骤1：部署本解决方案中间件。
- 步骤2：部署ComfyUI前端。
- 步骤3: 在ComfyUI页面调试并创建一个可用的工作流。
- 步骤4：根据创建的工作流部署新的Amazon SageMaker推理节点。


## 部署步骤
### 步骤1: 部署解决方案中间件
此自动化Amazon CloudFormation模板在亚马逊云科技中部署解决方案。

1. 登录到[AWS管理控制台](https://console.aws.amazon.com/)，点击链接[Extension-for-Stable-Diffusion-on-AWS-ComfyUI.template](https://console.aws.amazon.com/cloudformation/home?#/stacks/create/template?stackName=stable-diffusion-aws&templateURL=https://aws-gcr-solutions.s3.amazonaws.com/stable-diffusion-aws-extension-github-mainline/v1.6.0-cc5e0f3/custom-domain/Extension-for-Stable-Diffusion-on-AWS.template.json){:target="_blank"}。
2. 默认情况下，该模版将在您登录控制台后默认的区域启动。若需在指定的Amazon Web Service区域中启动该解决方案，请在控制台导航栏中的区域下拉列表中选择。
3. 在**创建堆栈**页面上，确认Amazon S3 URL文本框中显示正确的模板URL，然后选择**下一步**。
4. 在**制定堆栈详细信息**页面，为您的解决方案堆栈分配一个账户内唯一且符合命名要求的名称。
5. 在**参数**部分，在**Bucket**中填入一个有效的新的S3桶的名字（或之前部署的、用于本解决方案ComfyUI部分的S3桶名字）。在**email**处输入一个正确的电子邮件地址，以便接收将来的通知。在**SdExtensionApiKey**字段中请输入一个包含数字和字母组合的20个字符的字符串；如果未提供，默认为"09876543210987654321"。在**LogLevel**处选择您心仪的Lambda Log日志打印级别，默认ERROR才打印。点击**下一步**。
6. 在**配置堆栈选项**页面，选择**下一步**。
7. 在**审核**页面，查看并确认设置。确保选中确认模板将创建Amazon Identity and Access Management（IAM）资源的复选框。并确保选中AWS CloudFormation需要的其它功能的复选框。选择**提交**以部署堆栈。
8. 您可以在 AWS CloudFormation 控制台的 **状态** 列中查看堆栈的状态。您应该会在大约 15 分钟内收到**CREATE_COMPLETE**状态。

    !!! tip "贴士" 
        请及时检查您预留邮箱的收件箱，并在主题为“AWS Notification - Subscription Confirmation”的邮件中，点击“Confirm subscription”超链接，按提示完成订阅。


### 步骤2: 部署ComfyUI前端
步骤3将会为客户安装ComfyUI的前端。该前端自动内置了汉化插件、工作流发布云上等按钮，为客户提供更友好的UI交互界面。此自动化Amazon CloudFormation模板在亚马逊云科技中部署解决方案。

1. 点击[链接](https://aws-gcr-solutions.s3.amazonaws.com/extension-for-stable-diffusion-on-aws/comfy-v1.6.0.yaml){:target="_blank"}来下载ComfyUI前端部署的yaml文件。
2. 登录到[AWS管理控制台](https://console.aws.amazon.com/)，点击控制台右上角**Create Stack**, **With new resource(standard)**，页面跳转至创建堆栈。
3. 在**创建堆栈**页面上，选择**Choose an existing template**，在**特定模版**区域选择**Upload a template file**，从本地选择选择刚下载的yaml文件上传，然后选择**下一步**。
4. 在**制定堆栈详细信息**页面，为您的解决方案堆栈分配一个账户内唯一且符合命名要求的名称。在**参数**部分，**InstanceType**为选择部署的ec2的实例类型、**NumberOfInferencePorts**为推理环境数量（建议不超过5个）**StackName**来自于部署步骤第一大部分中成功部署堆栈的名称。**keyPairName**选择现有的一个EC2 Key Pair，点击**Next**。

    !!! tip "贴士"
        此处的EC2 Key Pair主要用于本地远程连接EC2。如果没有现有的，可以参考[官方手册](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/create-key-pairs.html){:target="_blank"}来创建。


5. 在**配置堆栈选项**页面，选择**下一步**。
6. 在**审核**页面，查看并确认设置。确保选中确认模板将创建Amazon Identity and Access Management（IAM）资源的复选框。并确保选中AWS CloudFormation需要的其它功能的复选框。选择**提交**以部署堆栈。
7. 您可以在 AWS CloudFormation 控制台的 **状态** 列中查看堆栈的状态。您应该会在大约 3 分钟内收到**CREATE_COMPLETE**状态。
8. 选择部署成功的堆栈，打开**Outputs**，点击**Designer**对应的链接，即可打开解决方案部署的ComfyUI前端，Designer的访问可能需要关闭VPN或者去掉10000端口后访问。**NumberOfInferencePortsStart**代表推理环境地址起始路径端口，按照部署数量端口地址依次增加，例如：当NumberOfInferencePorts填写3时，地址范围时，可访问的推理环境地址依次为：http://EC2地址:10001，http://EC2地址:10002，http://EC2地址:10003

    !!! tip "贴士"
        刚部署好贴士以后，需要稍作等待。如果打开链接后，看到提示“Comfy is Initializing or Starting”，表示后端在初始化ComfyUI过程中，请稍作等待，再次刷新页面确认。

### 步骤3: 在ComfyUI页面调试并创建一个可用的工作流。
可以参考[这里](../user-guide/ComfyUI/inference.md)中的“工作流的调试”子章节部分

### 步骤4: 部署新的Amazon SageMaker推理节点
在步骤1成功完成后，需要通过API方式部署所需的Amazon SageMaker推理节点。后续的新发布的ComfyUI工作流推理都将使用该推理节点的计算资源。

以下API代码中所需的ApiGatewayUrl及ApiGatewayUrlToken，可以在步骤1部署成功的堆栈**Outputs**标签页找到。

请打开任何可以运行代码的窗口，比如本地Macbook电脑的Terminal，运行如下API代码。

```
curl --location ‘此处填写您的api地址’ \
--header ‘x-api-key: 此处填写您的apikey’ \
--header ‘username: api’ \
--header ‘Content-Type: application/json’ \
--data-raw ‘{
    “workflow_name”:“此处填写您创建的workflow名称“,
    “endpoint_name”: “当无需关联workflow时需要填写您要创建的推理端点名字",
    “service_type”: “comfy”,
    “endpoint_type”: “Async”,
    “instance_type”: “实例类型”,
    “initial_instance_count”: 1,
    “min_instance_number”: 1,
    “max_instance_number”: 2,
    “autoscaling_enabled”: true,
    “assign_to_roles”: “test”
    “assign_to_roles”: [ “test” ]
}’
```

!!! Important "注意" 
    如果是相对复杂的workflow 注意选择异步推理节点类型，否则受限于service最长等待30s，会出现调用推理超时的情况。


后续如需要删除Amazon SageMaker推理节点，可通过以下API完成。
```
curl --location --request DELETE 'https://此处填ApiGatewayUrl地址/endpoints' \
--header 'username: api' \
--header 'x-api-key: 此处填ApiGatewayUrlToken' \
--header 'Content-Type: application/json' \
--data-raw '{
    "endpoint_name_list": [
        "comfy-real-time-test-34"//填要删除的endpoint名字
    ]
}'
```

!!! Important "注意" 
    不建议直接进去SageMaker console直接删除endpoint，容易造成数据不一致的隐患。





