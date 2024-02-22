在部署解决方案之前，建议您先查看本指南中有关架构图和区域支持等信息。然后按照下面的说明配置解决方案并将其部署到您的帐户中。

部署时间：约 20 分钟

## 前提条件
<!-- 用户需提前部署好本地的[Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)。 -->
用户需要提前准备一台运行linux系统的电脑

## 部署概述
在亚马逊云科技上部署本解决方案主要包括以下过程：

- 步骤0：部署Stable Diffusion WebUI（若您没有部署过Stable Diffusion WebUI开源项目）。
- 步骤1：部署本解决方案中间件。
- 步骤2: 配置API Url和API Token。
!!! Important "提示" 
    本解决方案提供两种使用方法：通过UI界面及通过后端API直接调用。只有当用户需要通过UI界面使用时，需要执行步骤0，以安装另一开源项目Stable Diffusion webUI，从而可以通过webUI的方式进行业务操作。



## 部署步骤

### 步骤0 - Linux：部署Stable Diffusion WebUI (Linux)。

1. 登录到[AWS管理控制台](https://console.aws.amazon.com/)，进入[WebUI on EC2](https://console.aws.amazon.com/cloudformation/home?#/stacks/create/template?stackName=stable-diffusion-aws&templateURL=https://aws-gcr-solutions-us-east-1.s3.amazonaws.com/extension-for-stable-diffusion-on-aws/ec2.yaml)。

2. 在**堆栈**页面上，选择**创建堆栈**，然后选择**使用新资源（标准）**。

3. 在**指定模板**页面上，选择**模板准备就绪**，选择**上传模板文件**，选择步骤1中下载的模板，最后选择**下一步**。

4. 在**指定堆栈名称和参数**页面上，输入堆栈名称到堆栈名称框中，然后选择**下一步**。

5. 在**设置堆栈选项**页面上，选择**下一步**。

6. 在**审核**页面上，查看堆栈的详细信息，然后选择**提交**。

7. 等待堆栈创建完成。

8. 查找CloudFormation堆栈的输出值，并通过单击**WebUIURL**值中的链接导航到Web界面，注意，在堆栈成功创建后，需要额外等待5分钟以完成内部设置。

### 步骤0 - Windows：部署Stable Diffusion WebUI (Windows)。
1. 启动一台Windows Server，通过RDP登录。
2. 参考[链接](https://docs.aws.amazon.com/zh_cn/AWSEC2/latest/WindowsGuide/install-nvidia-driver.html)安装NVIDIA驱动程序。
3. 访问[Python网站](https://www.python.org/downloads/release/python-3106/)，下载Python并安装，记得要选上 Add Python to Path。
4. 访问[Git网站](https://git-scm.com/download/win)，下载Git并安装。
5. 打开PowerShell，下载本方案源码（git clone https://github.com/awslabs/stable-diffusion-aws-extension）。
6. 在源码中，执行 install.bat。
7. 在下载的stable-diffusion-webui文件夹中，执行webui-user.bat。


### 步骤1：部署本解决方案中间件。

此自动化Amazon CloudFormation模板在亚马逊云科技中部署解决方案。

1. 登录到[AWS管理控制台](https://console.aws.amazon.com/)，点击链接[Stable-Diffusion-AWS-Extension.template](https://console.aws.amazon.com/cloudformation/home?#/stacks/create/template?stackName=stable-diffusion-aws&templateURL=https://aws-gcr-solutions.s3.amazonaws.com/stable-diffusion-aws-extension-github-mainline/latest/custom-domain/Stable-diffusion-aws-extension-middleware-stack.template.json){:target="_blank"}。
2. 默认情况下，该模版将在您登录控制台后默认的区域启动。若需在指定的Amazon Web Service区域中启动该解决方案，请在控制台导航栏中的区域下拉列表中选择。
3. 在**创建堆栈**页面上，确认Amazon S3 URL文本框中显示正确的模板URL，然后选择**下一步**。
4. 在**制定堆栈详细信息**页面，为您的解决方案堆栈分配一个账户内唯一且符合命名要求的名称。
5. 在**参数**部分，在**Bucket**中填入一个有效的新的s3桶的名字。在**EcrImageTag**字段选择方案对应的ECR镜像的tag（如果无需修改就保持默认值即可。更多tag的说明请点击这个[link](ecr_image_param.md)）。在**email**处输入一个正确的电子邮件地址，以便接收将来的通知。在**SdExtensionApiKey**字段中请输入一个包含数字和字母组合的20个字符的字符串；如果未提供，默认为"09876543210987654321"。在**LogLevel**处选择您心仪的Lambda Log日志打印级别，默认ERROR才打印。在**UtilsCpuInstType**选择Amazon EC2的实例类型，主要用于包括模型创建、模型合并等操作。点击**下一步**。

    !!! Important "提示" 
        请不要自行改动**EcrImageTag**。如有需求，请联系解决方案团队。

6. 在**配置堆栈选项**页面，选择**下一步**。
7. 在**审核**页面，查看并确认设置。确保选中确认模板将创建Amazon Identity and Access Management（IAM）资源的复选框。并确保选中AWS CloudFormation需要的其它功能的复选框。选择**提交**以部署堆栈。
8. 您可以在 AWS CloudFormation 控制台的 **状态** 列中查看堆栈的状态。您应该会在大约 15 分钟内收到**CREATE_COMPLETE**状态。

    !!! Important "提示" 
        请及时检查您预留邮箱的收件箱，并在主题为“AWS Notification - Subscription Confirmation”的邮件中，点击“Confirm subscription”超链接，按提示完成订阅。




### 步骤2: 配置API Url和API Token
堆栈创建成功后，您可以参考[这里](../user-guide/multi-user.md)进行后续配置工作。


<!-- 1. 访问[AWS CloudFormation控制台](https://console.aws.amazon.com/cloudformation/)。

2. 从堆栈列表中选择方案的根堆栈，而不是嵌套堆栈。列表中嵌套堆栈的名称旁边会显示嵌套（NESTED）。

3. 打开输出（Outputs）标签页，找到**APIGatewayUrl**和**ApiGatewayUrlToken**对应的数值，并复制。

4. 打开Stable Diffusion WebUI中的**Amazon SageMaker**标签页，在**API URL**文本框粘贴步骤3得到的URL。在**API Token**输入步骤3得到的token。点击**Test Connection**，会得到**Successfully Connected**的确认信息。

5. 点击**Update Setting**更新配置文件，这样下次就能得到对应的信息 -->


<!-- ## 后续操作
堆栈创建成功后，您可以在AWS CloudFormation的输出（Outputs）标签页中查询相关信息。 -->
