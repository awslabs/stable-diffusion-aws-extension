在部署解决方案之前，建议您先查看本指南中有关架构图和区域支持等信息。然后按照下面的说明配置解决方案并将其部署到您的帐户中。

部署时间：约 20 分钟

## 前提条件
<!-- 用户需提前部署好本地的[Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)。 -->
- 用户需要提前准备一台运行 Linux 系统的电脑。
- 安装并且配置好了[aws cli](https://aws.amazon.com/cli/)。
- 部署过上一个版本的Stable Diffusion Webui AWS插件。

## 部署概述
在亚马逊云科技上部署本解决方案主要包括以下过程：

- 步骤1：更新Stable Diffusion WebUI及对应插件版本。
- 步骤2：登录AWS Console后，在CloudFormation中更新已有的Stable Diffusion AWS extension模版。

## 部署步骤

### 步骤1 - Linux：更新 Stable Diffusion WebUI (Linux)

1. 从 [链接](https://aws-gcr-solutions-us-east-1.s3.amazonaws.com/extension-for-stable-diffusion-on-aws/ec2.yaml){:target="_blank"} 下载CloudFormation模板。
2. 登录到[AWS管理控制台](https://console.aws.amazon.com/){:target="_blank"}，进入[CloudFormation控制台](https://console.aws.amazon.com/cloudformation/){:target="_blank"}。
3. 在**堆栈**页面上，选择**创建堆栈**，然后选择**使用新资源（标准）**。
4. 在**指定模板**页面上，选择**模板准备就绪**，选择**上传模板文件**，选择步骤1中下载的模板，最后选择**下一步**。
5. 在**指定堆栈名称和参数**页面上，输入堆栈名称到堆栈名称框中，然后选择**下一步**。
6. 在**设置堆栈选项**页面上，选择**下一步**。
7. 在**审核**页面上，查看堆栈的详细信息，然后选择**提交**。
8. 等待堆栈创建完成。
9. 查找CloudFormation堆栈的输出值，并通过单击**WebUIURL**值中的链接导航到Web界面，注意，在堆栈成功创建后，需要额外等待 30 分钟以完成内部设置。

### 步骤1 - Windows：更新 Stable Diffusion WebUI (Windows)
1. 启动一台Windows Server，通过RDP登录。
2. 参考[链接](https://docs.aws.amazon.com/zh_cn/AWSEC2/latest/WindowsGuide/install-nvidia-driver.html)安装NVIDIA驱动程序。
3. 访问[Python网站](https://www.python.org/downloads/release/python-3106/)，下载Python并安装，记得要选上 Add Python to Path。
4. 访问[Git网站](https://git-scm.com/download/win)，下载Git并安装。
5. 打开PowerShell，下载本方案源码（git clone https://github.com/awslabs/stable-diffusion-aws-extension）。
6. 在源码中，执行 install.bat。
7. 在下载的stable-diffusion-webui文件夹中，执行webui-user.bat。


### 步骤2：在 CloudFormation 中更新已有的 Stable Diffusion AWS Extension

1. 打开 AWS 管理控制台[（https://console.aws.amazon.com）](https://console.aws.amazon.com)并登录。
2. 在服务菜单中选择 "CloudFormation"，找到之前已经部署的本方案的堆栈，并选中它，点击页面右上方的“Update”。
3. 在“Update Stack"中，选择 "Replace current template"，并在“Amazon S3 URL"部分填入最新[部署模版链接](https://aws-gcr-solutions.s3.amazonaws.com/stable-diffusion-aws-extension-github-mainline/latest/custom-domain/Extension-for-Stable-Diffusion-on-AWS.template.json)，点击“Next”。
4. 在“Configure stack options"界面，选择“Next”。
5. 在“Review”界面，勾选必要选择框并选择“Submit”。
6. CloudFormation 将开始更新堆栈，这可能需要一些时间。你可以在 "Stacks" 页面上监视堆栈的状态。


## 注意事项
1. 更新 1.5.0 需重新创建 Endpoint
2. WebUI 客户端和中间件API的版本应保持一致
3. WebUI 客户端建议创建新的 EC2 实例
4. 中间件 API 版本 1.4.0 可直接 Update，1.3.0 先卸载再安装
5. 如果涉及到已经通过 API 集成的服务，请浏览 API 文档[升级权限校验方式](https://awslabs.github.io/stable-diffusion-aws-extension/zh/developer-guide/api_authentication/)，并做好上线前的测试工作




<!-- ### 步骤2：通过安装脚本安装插件Stable Diffusion AWS Extension。
1. 在提前准备的运行linux的电脑的工作目录下，运行以下命令下载最新的安装脚本
```
wget https://raw.githubusercontent.com/awslabs/stable-diffusion-aws-extension/main/install.sh
```
2. 运行安装脚本
```
sh install.sh
```
3. 移步到install.sh下载的stable-diffusion-webui文件夹
```
cd stable-diffusion-webui
```
4. 对于不带GPU的机器，可以通过以下命令启动webui
```
./webui.sh --skip-torch-cuda-test
```
5. 对于带GPU的机器，可以通过以下命令启动webui
```
./webui.sh
``` -->



<!-- 
1. 访问[AWS CloudFormation控制台](https://console.aws.amazon.com/cloudformation/)。

2. 从堆栈列表中选择方案的根堆栈，而不是嵌套堆栈。列表中嵌套堆栈的名称旁边会显示嵌套（NESTED）。

3. 打开输出（Outputs）标签页，找到**APIGatewayUrl**和**ApiGatewayUrlToken**对应的数值，并复制。

4. 打开Stable Diffusion WebUI中的**Amazon SageMaker**标签页，在**API URL**文本框粘贴步骤3得到的URL。在**API Token**输入步骤3得到的token。

5. 点击**Test Connection & Update Setting**更新配置文件，这样下次就能得到对应的信息
 -->

<!-- ## 后续操作
堆栈创建成功后，您可以在AWS CloudFormation的输出（Outputs）标签页中查询相关信息。 -->
