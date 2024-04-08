Before you launch the solution, review the architecture, supported regions, and other considerations discussed in this guide. Follow the step-by-step instructions in this section to configure and deploy the solution into your account.

**Time to deploy**: Approximately 20 minutes.

## Prerequisites

- The user needs to prepare a computer running a Linux system in advance.
- Install and configure [aws cli](https://aws.amazon.com/cli/).
- Deploy the previous version of the Stable Diffusion Webui AWS plugin.

## Deployment overview
Use the following steps to deploy this solution on AWS.

- Step 1: Update Stable Diffusion WebUI.
- Step 2: After logging into the AWS Console, update the existing Stable Diffusion AWS extension template in CloudFormation.


## Deployment steps

### Step 1 - Linux：Update Stable Diffusion WebUI (Linux).

1. Download the CloudFormation Template from [link](https://aws-gcr-solutions-us-east-1.s3.amazonaws.com/extension-for-stable-diffusion-on-aws/ec2.yaml){:target="_blank"}

2. Sign in to the [AWS Management Console](https://console.aws.amazon.com/){:target="_blank"} and go to [CloudFormation console](https://console.aws.amazon.com/cloudformation/){:target="_blank"}

3. On the Stacks page, choose **Create stack**, and then choose **With new resources (standard)**.

4. On the **Specify template** page, choose **Template is ready**, choose **Upload a template file**, and then browse for the template that is downloaded in step 1, and then choose **Next**.

5. On the **Specify stack details** page, type a stack name in the Stack name box, then choose **Next**.

6. On the **Configure stack options** page, choose **Next**.

7. On the **Review** page, review the details of your stack, and choose **Submit**.

8. Wait until the stack is created.

9. Find the output value of the CloudFormation stack, and navigate to the WebUI by clicking the link in the **WebUIURL** value, note you need to wait extra 30 minutes to wait for the internal setup complete after the stack been created successfully.

### Step 1 - Windows: Update Stable Diffusion WebUI (Windows).
1. Start a Windows Server and log in via RDP.
2. Refer to [this link](https://docs.aws.amazon.com/en_us/AWSEC2/latest/WindowsGuide/install-nvidia-driver.html) to install the NVIDIA driver.
3. Visit the [Python website](https://www.python.org/downloads/release/python-3106/), download Python, and install it. Remember to check "Add Python to Path" during installation.
4. Visit the [Git website](https://git-scm.com/download/win), download Git, and install it.
5. Open PowerShell and download the source code of this project by executing: `git clone https://github.com/awslabs/stable-diffusion-aws-extension`.
6. Inside the source code directory, run `install.bat`.
7. In the downloaded `stable-diffusion-webui` folder, run `webui-user.bat`.


### Step 2：Update the existing Stable Diffusion AWS extension template in CloudFormation.

1. Open the AWS Management Console [(https://console.aws.amazon.com)](https://console.aws.amazon.com) and log in.
2. Select "CloudFormation" from the service menu, find the stack deployed for this solution, and select it, click **Update** in the upper right.
3. In **Update Stack**, select **Replace current template**, enter latest CloudFormation [link](https://aws-gcr-solutions.s3.amazonaws.com/stable-diffusion-aws-extension-github-mainline/latest/custom-domain/Extension-for-Stable-Diffusion-on-AWS.template.json) in **Amazon S3 URL** and click **Next**.
4. In **Configure stack options**, click **Next**.
5. In **Review**, select acknowledge option and click **Submit**. 
6. CloudFormation will start updating the stack, which may take some time. You can monitor the status of the stack on the **Stacks** page.


## Notice
1. SageMaker Inference Endpoints need to delete and deploy new after updating solution to V1.5.0
2. The version of webUI and middleware should match.
3. Recommend to deploy new webUI on EC2. 
4. Middleware API version 1.4.0 can be updated directly, while version 1.3.0 needs to be uninstalled first and then reinstalled.
5. If it involves services already integrated through an API, please review the API documentation for [upgrading permission verification](https://awslabs.github.io/stable-diffusion-aws-extension/zh/developer-guide/api_authentication/) methods, and conduct thorough testing before going live.





