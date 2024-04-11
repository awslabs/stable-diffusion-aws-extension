## 连接Stable Diffusion WebUI与AWS账号

## 要求

您需要部署好解决方案。

## 步骤

1. 访问[AWS CloudFormation控制台](https://console.aws.amazon.com/cloudformation/)。
2. 从堆栈列表中选择方案的堆栈。
3. 打开输出（Outputs）标签页，找到**APIGatewayUrl**对应的URL，并复制。
4. 打开Stable Diffusion WebUI中的**Amazon SageMaker**标签页，在**API URL**文本框粘贴步骤3得到的URL。在**API Token**输入 token，设置用户名和密码。
5. 点击**Test Connection & Update Setting** 。
