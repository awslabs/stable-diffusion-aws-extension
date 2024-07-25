在部署解决方案之前，建议您先查看本指南中有关架构图和区域支持等信息。然后按照下面的说明配置解决方案并将其部署到您的帐户中。

部署时间：约 20 分钟

## 部署概述
在亚马逊云科技上部署本解决方案（ComfyUI部分）主要包括以下过程：

- 步骤1：部署本解决方案中间件。
- 步骤2：部署ComfyUI前端。

部署完成后，具体使用流程，请参考[ComfyUI用户手册](../user-guide/ComfyUI/inference.md)


## 部署步骤
### 步骤1: 部署解决方案中间件
此自动化Amazon CloudFormation模板在亚马逊云科技中部署解决方案。

1. 登录到[AWS管理控制台](https://console.aws.amazon.com/)，点击链接[Extension for Stable Diffusion on AWS](https://console.aws.amazon.com/cloudformation/home?#/stacks/create/template?stackName=stable-diffusion-aws&templateURL=https://aws-gcr-solutions.s3.amazonaws.com/stable-diffusion-aws-extension-github-mainline/latest/custom-domain/Extension-for-Stable-Diffusion-on-AWS.template.json){:target="_blank"}。
2. 默认情况下，该模版将在您登录控制台后默认的区域启动。若需在指定的Amazon Web Service区域中启动该解决方案，请在控制台导航栏中的区域下拉列表中选择。
3. 在**创建堆栈**页面上，确认Amazon S3 URL文本框中显示正确的模板URL，然后选择**下一步**。
4. 在**制定堆栈详细信息**页面，为您的解决方案堆栈分配一个账户内唯一且符合命名要求的名称。部署参数参考下表。点击**下一步**。

    |参数|说明|建议|
    |:-------------|:--------------|:--------------|
    |APIEndpointType|如需API调用，定义该API的类别，选项REGIONAL / PRIVATE / EDGE|默认Regional|
    |Bucket|填入一个有效的新的S3桶的名字（或之前部署的、用于本解决方案ComfyUI部分的S3桶名字）||
    |email|输入一个正确的电子邮件地址，以便接收将来的通知||
    |SdExtensionApiKey|请输入一个包含数字和字母组合的20个字符的字符串|默认为"09876543210987654321"|
    |LogLevel|择您心仪的Lambda Log日志打印级别|默认ERROR才打印|

5. 在**配置堆栈选项**页面，选择**下一步**。
6. 在**审核**页面，查看并确认设置。确保选中确认模板将创建Amazon Identity and Access Management（IAM）资源的复选框。并确保选中AWS CloudFormation需要的其它功能的复选框。选择**提交**以部署堆栈。
7. 您可以在 AWS CloudFormation 控制台的 **状态** 列中查看堆栈的状态。您应该会在大约 15 分钟内收到**CREATE_COMPLETE**状态。

    !!! tip "贴士" 
        请及时检查您预留邮箱的收件箱，并在主题为“AWS Notification - Subscription Confirmation”的邮件中，点击“Confirm subscription”超链接，按提示完成订阅。


### 步骤2: 部署ComfyUI前端
步骤2将会为客户安装ComfyUI的前端。该前端自动内置了汉化插件、工作流发布云上等按钮，为客户提供更友好的UI交互界面。此自动化Amazon CloudFormation模板在亚马逊云科技中部署。

1. 登录到[AWS管理控制台](https://console.aws.amazon.com/)，点击控制台右上角**Create Stack**, **With new resource(standard)**，页面跳转至创建堆栈。
2. 在**创建堆栈**页面上，选择**Choose an existing template**，在**特定模版**区域选择**Amazon S3 URLe**，填入该[部署模版链接](https://aws-gcr-solutions.s3.amazonaws.com/extension-for-stable-diffusion-on-aws/comfy.yaml)，然后选择**下一步**。
3. 在**制定堆栈详细信息**页面，为您的解决方案堆栈分配一个账户内唯一且符合命名要求的名称。在**参数**部分，部署参数说明如下。点击**Next**。

    !!! tip "贴士"
        此处的EC2 Key Pair主要用于本地远程连接EC2。如果没有现有的，可以参考[官方手册](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/create-key-pairs.html){:target="_blank"}来创建。

    |参数|说明|建议|
    |:-------------|:--------------|:--------------|
    |InstanceType |部署的ec2的实例类型 | 如果是涉及推理动图、视频等，建议G6、G5机器 |
    |NumberOfInferencePorts|推理环境数量|建议不超过5个|
    |StackName|来自于部署步骤1中成功部署堆栈的名称||
    |keyPairName|选择现有的一个EC2 Key Pair||

4. 在**配置堆栈选项**页面，选择**下一步**。
5. 在**审核**页面，查看并确认设置。确保选中确认模板将创建Amazon Identity and Access Management（IAM）资源的复选框。并确保选中AWS CloudFormation需要的其它功能的复选框。选择**提交**以部署堆栈。
6. 您可以在 AWS CloudFormation 控制台的 **状态** 列中查看堆栈的状态。您应该会在大约 3 分钟内收到**CREATE_COMPLETE**状态。
7. 选择部署成功的堆栈，打开**Outputs**，点击**Designer**对应的链接，即可打开解决方案部署的ComfyUI前端，Designer的访问可能需要关闭VPN或者去掉10000端口后访问。**NumberOfInferencePortsStart**代表推理环境地址起始路径端口，按照部署数量端口地址依次增加，例如：当NumberOfInferencePorts填写2时，地址范围时，可访问的推理环境地址依次为：http://EC2地址:10001，http://EC2地址:10002.

    |角色|功能|端口|
    |:-------------|:--------------|:--------------|
    |主美/工作流管理| 能够安装新的custom nodes，在EC2上调试工作流，发布工作流、环境至Amazon SageMaker。同时可以调用SageMaker资源、选中已发布的工作流进行推理验证 | http://EC2地址|
    |普通美术| 从该端口进入的界面，可以选择主美已发布的工作流，简单修改推理参数后，勾选“Prompt on AWS”后、调用Amazon SageMaker进行推理|当NumberOfInferencePorts填写3时，地址范围时，可访问的推理环境地址依次为：<ul><li>http://EC2地址:10001 </li><li>http://EC2地址:10002 </li><li>http://EC2地址:10003</li></ul>|

    !!! tip "贴士"
        刚部署好贴士以后，需要稍作等待。如果打开链接后，看到提示“Comfy is Initializing or Starting”，表示后端在初始化ComfyUI过程中，请稍作等待，再次刷新页面确认。







