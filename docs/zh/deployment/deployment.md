在部署解决方案之前，建议您先查看本指南中有关架构图和区域支持等信息。然后按照下面的说明配置解决方案并将其部署到您的帐户中。

部署时间：约 15 分钟

## 前提条件
用户需提前部署好本地的[Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)。

## 部署概述
在亚马逊云科技上部署本解决方案主要包括以下过程：

- 步骤1：在您的亚马逊云科技账户中启动Amazon CloudFormation模板。
- 步骤2：在您的现有Stable Diffusion WebUI上安装插件Stable Diffusion AWS Extension。


## 部署步骤



### 步骤1：在您的亚马逊云科技账户中启动Amazon CloudFormation模板。

此自动化Amazon CloudFormation模板在亚马逊云科技中部署解决方案。

1. 登录到AWS管理控制台，点击链接创建AWS CloudFormation模版。
2. 默认情况下，该模版将在您登录控制台后默认的区域启动。若需在指定的Amazon Web Service区域中启动该解决方案，请在控制台导航栏中的区域下拉列表中选择。
3. 在**创建堆栈**页面上，确认Amazon S3 URL文本框中显示正确的模板URL，然后选择**下一步**。
4. 在**制定堆栈详细信息**页面，为您的解决方案堆栈分配一个账户内唯一且符合命名要求的名称。在**参数**部分，请输入正确的邮箱用来未来接受通知。
!!! Important "提示" 
    请及时检查您预留邮箱的收件箱，并在主题为“AWS Notification - Subscription Confirmation”的邮件中，点击“Confirm subscription”超链接，按提示完成订阅。

5. 在**配置堆栈选项**页面，选择**下一步**。
6. 在**审核**页面，查看并确认设置。确保选中确认模板将创建Amazon Identity and Access Management（IAM）资源的复选框。并确保选中AWS CloudFormation需要的其它功能的复选框。选择**提交**以部署堆栈。

您可以在AWS CloudFormation控制台的状态列中查看堆栈的状态。创建完成后即可看到状态为CREATE_COMPLETE。

### 步骤2：在您的现有Stable Diffusion WebUI上安装插件Stable Diffusion AWS Extension。
1. 打开已部署的Stable Diffusion WebUI界面，进入**Extensions**标签页 - **Install from URL**子标签页，在**URL from extension's git repository**文本框输入本解决方案repository地址 [https://github.com/aws-samples/stable-diffusion-aws-extension.git](https://github.com/aws-samples/stable-diffusion-aws-extension.git)，点击**Install**。
2. 点击**Installed**子标签页，点击**Apply and restart UI**，WebUI会多出一个**Amazon SageMaker**标签页，表明已完成插件安装。


### 后续操作
堆栈创建成功后，您可以在AWS CloudFormation的输出（Outputs）标签页中查询相关信息。
