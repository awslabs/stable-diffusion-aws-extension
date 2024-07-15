Before deploying the solution, it is recommended that you first review information in this guide regarding architecture diagrams and regional support. Then, follow the instructions below to configure the solution and deploy it to your account.

Deployment time: arount 20 minutes.

## Deployment Summary
Deploying this solution (ComfyUI portion) on Amazon Web Services primarily involves the following processes:

- Step 1: Deploy the middleware of the solution.
- Step 2: Deploy ComfyUI frontend.

!!! tip 
        You can refer to the ComfyUI section in the FAQ chapter if you encounter deployment issues.

## Deployment Steps
### Step 1: Deploy the middleware of the solution
This automated Amazon CloudFormation template deploys the solution in Amazon Web Services.

1. Sign in to the [AWS Management Console](https://console.aws.amazon.com/)，and use [Extension for Stable Diffusion on AWS](https://console.aws.amazon.com/cloudformation/home?#/stacks/create/template?stackName=stable-diffusion-aws&templateURL=https://aws-gcr-solutions.s3.amazonaws.com/stable-diffusion-aws-extension-github-mainline/latest/custom-domain/Extension-for-Stable-Diffusion-on-AWS.template.json){:target="_blank"} to create the stack.
2. By default, this template will launch in the default region after you log in to the console. To launch this solution in a specified Amazon Web Services region, please select the desired region from the region drop-down list in the console's navigation bar.
3. On the **Create Stack** page，confirm that the correct template URL has been entered in the **Amazon S3 URL** text box, then select **Next**.
4. On the **Specify stack details** page, assign a unique name within your account that meets the naming requirements for your solution stack. Refer to the table below for deployment parameters. Click **Next**.

    |Parameter|Description|Recommendation|
    |:-------------|:--------------|:--------------|
    |Bucket|Enter a valid new S3 bucket name (or the name of a previously deployed S3 bucket used for the ComfyUI section of this solution)||
    |email|Enter a valid email address for further notification receivement||
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

### Step3: 在ComfyUI页面调试并创建一个可用的工作流。
可以参考[这里](../user-guide/ComfyUI/inference.md)中的“工作流的调试”子章节部分

### Step 4: Deploy new Amazon SageMaker inference endpoint
After successfully completing step 1, you need to deploy the required Amazon SageMaker inference nodes using API. Subsequent deployments of new ComfyUI workflow inferences will utilize the computational resources of these inference nodes.

The `ApiGatewayUrl` and `ApiGatewayUrlToken` required in the following API code can be found in the **Outputs** tab of the stack deployed successfully in step 1.

Please open any command-line interface capable of running code, such as Terminal on a local MacBook, and execute the following API code.

```
curl --location ‘YourAPIURL/endpoints’ \
--header ‘x-api-key: Your APIkey’ \
--header ‘username: api’ \
--header ‘Content-Type: application/json’ \
--data-raw ‘{
    “workflow_name”:“Please fill the name of template you just released“,
    “endpoint_name”: “When you don't need to associate it with a workflow, you should fill in the name of the inference endpoint you want to create",
    “service_type”: “comfy”,
    “endpoint_type”: “Async”,
    “instance_type”: “instance type”,
    “initial_instance_count”: 1,
    “min_instance_number”: 1,
    “max_instance_number”: 2,
    “autoscaling_enabled”: true,
    “assign_to_roles”: “test”
    “assign_to_roles”: [ “test” ]
}’
```

!!! Important 
    If your workflow is relatively complex, it's important to select asynchronous inference node types. Otherwise, you may encounter timeout issues due to the service's maximum wait time of 30 seconds for synchronous calls.



Delete corresponding Amazon SageMaker endpoint, can be executed as below:
```
curl --location --request DELETE 'https://please fill ApiGatewayUrl/endpoints' \
--header 'username: api' \
--header 'x-api-key: please type the ApiGatewayUrlToken' \
--header 'Content-Type: application/json' \
--data-raw '{
    "endpoint_name_list": [
        "comfy-real-time-test-34"//type the name of the endpoint
    ]
}'
```

!!! Important
    It's not recommended to directly delete endpoints from the SageMaker console as it can potentially lead to inconsistencies in data.






