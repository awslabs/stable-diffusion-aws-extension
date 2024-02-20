## 连接Stable Diffusion WebUI与AWS账号

### 前提条件
您需要已经成功完成解决方案的部署。

*可选项*
为了保证AWS Extension插件同第三方插件之间（controlnet）版本的兼容性，您可以运行以下命令检查AWS Extension所支持的第三方插件的最小支持版本。
```bash
./preflight.sh
```
![preflight](../images/preflight.png)

如果您对第三方插件的版本没有特别的要求，您可以通过执行以下命令安装版本兼容的第三方插件（controlnet）。

```bash
# Clone sd-webui-controlnet
git clone https://github.com/Mikubill/sd-webui-controlnet.git

# Go to sd-webui-controlnet directory and reset to specific commit
cd sd-webui-controlnet
git reset --hard 7c674f8364227d63e1628fc29fa8619d33c56674
cd ..

```

<!-- ### 操作步骤
1. 访问[AWS CloudFormation控制台](https://console.aws.amazon.com/cloudformation/)。
2. 从堆栈列表中选择方案的根堆栈，而不是嵌套堆栈。列表中嵌套堆栈的名称旁边会显示嵌套（NESTED）。
3. 打开输出（Outputs）标签页，找到**APIGatewayUrl**对应的URL，并复制。
4. 打开Stable Diffusion WebUI中的**Amazon SageMaker**标签页，在**API URL**文本框粘贴步骤3得到的URL。在**API Token**输入09876543210987654321。点击**Update Setting**，会得到*Successfully Updated Config*的确认信息。
5. 点击**Test Connection**，得到*Successfully Connected*确认信息，表明现在Stable Diffusion WebUI已经成功与后端部署堆栈的AWS账户链接。 -->
