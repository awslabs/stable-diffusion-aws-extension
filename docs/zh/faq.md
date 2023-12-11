# 常见问题解答

## 一般问题

**问：什么是Stable Diffusion亚马逊云科技插件解决方案？**
Stable Diffusion亚马逊云科技插件解决方案通过为社区提供插件和云资源模版方式，帮助现有客户将现有Stable Diffusion的模型训练，推理和调优等任务负载从本地服务器迁移至Amazon SageMaker，利用云上弹性资源加速模型迭代，避免单机部署所带来的性能瓶颈。

**问：该解决方案中支持哪些原生功能/第三方插件？**
本解决方案支持多种Stable Diffusion WebUI原生功能及第三方插件。请参考[支持的具体功能列表及版本](./solution-overview/features-and-benefits.md)等，了解更多细节。

**问：这个解决方案的许可证是什么？**
本解决方案是根据[Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0){:target="_blank"}许可证提供的。 它是一个由 Apache 软件基金会编写的自由软件许可证。 它允许用户为任何目的使用该软件，分发、修改该软件，并根据许可证的条款分发该软件的修改版本，而不必担心版权费。

**问：我如何提交功能请求或错误报告？**
你可以通过GitHub问题提交[功能请求](https://github.com/awslabs/stable-diffusion-aws-extension/issues/new?assignees=&labels=feature-request%2Cneeds-triage&projects=&template=feature_request.yml&title=%28module+name%29%3A+%28short+issue+description%29){:target="_blank"}和[错误报告](https://github.com/awslabs/stable-diffusion-aws-extension/issues/new?assignees=&labels=bug%2Cneeds-triage&projects=&template=bug_report.yml&title=%28module+name%29%3A+%28short+issue+description%29){:target="_blank"}。


## 安装和配置

**问：我安装第三方插件和本解决方案插件的顺序有要求吗？**

目前推荐用户先安装本解决方案支持的第三方插件后，再安装本解决方案插件。而该安装顺序打乱也可以，但是需要您重启WebUI，即可保证功能成功运行。

**问：我安装后成功webUI后，浏览器访问不了，该怎么解决？**

在用浏览器访问webUI链接前，请确保相关端口已经打开，没有被防火墙阻拦。

**问：我应该如何更新解决方案？**

目前推荐用户不要频繁通过更新CloudFormation部署堆栈的方式更新解决方案。如果有更新需要，建议成功卸载现有解决方案堆栈后，再次根据CloudFormation模版部署新的堆栈。只要非第一次部署CloudFormation，请在部署时，区域‘Bucket’填入之前部署使用的S3桶名称，‘DeployedBefore’选择yes，以保证重新部署CloudFormation成功。

**问：我应该在同一台电脑上更换登录用户？**

您可以通过另开一个无痕浏览器的方式，登录另一个用户账户。

**问：我如何去掉本地推理的选项，让我的webUI只能支持云上推理？**

您可以打开webUI的主页面，进入**Settings**标签页，选择左侧的*User interface*标签栏，找到以下区域‘[info]
 Quicksettings list (setting entries that appear at the top of page rather than in settings tab) (requires Reload UI)‘，不选中‘sd_model_checkpoint'。以上操作完成后，点击最上方‘Apply setting' 而后 'Reload UI'，来让此改动生效。重启webUI后，您就会发现，原本界面本地选择推理底模的左上角下拉菜单消失，用户将只会有云上推理的选项。


## 成本

 **问：使用此解决方案如何收费和计费？**
该解决方案可免费使用，您需要承担运行该解决方案时使用的 AWS 服务的费用。 您只需为使用的内容付费，没有最低费用或设置费用。 有关详细的成本估算，请参阅[成本预估](./cost.md)部分。