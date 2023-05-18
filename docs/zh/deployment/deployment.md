在部署解决方案之前，建议您先查看本指南中有关架构图和区域支持等信息。然后按照下面的说明配置解决方案并将其部署到您的帐户中。

部署时间：约 XX 分钟

## 前提条件
（此处建议列出需要的最小配置）
建议放一下

## 部署概述
在亚马逊云科技上部署本解决方案主要包括以下过程：

- 步骤1：在您的亚马逊云科技账户中启动Amazon CloudFormation模板。
- 步骤2：在您的本地安装Stable Diffusion WebUI。
- 步骤3：在您的现有Stable Diffusion WebUI上安装插件 Stable Diffusion AWS Extension.
- 步骤4：在您的Stable Diffusion WebUI中的‘Amazon SageMaker'标签页输入API URL及API Token，测试链接并获得‘Success ’。


## 部署步骤

此自动化Amazon CloudFormation模板在亚马逊云科技中部署解决方案。

1. 登录到AWS管理控制台，点击链接创建AWS CloudFormation模版。
2. 默认情况下，该模版将在您登录控制台后默认的区域启动。若需在指定的Amazon Web Service区域中启动该解决方案，请在控制台导航栏中的区域下拉列表中选择。
3. 在创建堆栈页面上，确认Amazon S3 URL文本框中显示正确的模板URL，然后选择下一步。
4. 

