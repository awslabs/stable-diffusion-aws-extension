Before you launch the solution, review the architecture, supported regions, and other considerations discussed in this guide. Follow the step-by-step instructions in this section to configure and deploy the solution into your account.

**Time to deploy**: Approximately 20 minutes.

## Prerequisites
Users need to prepare a computer-running linux system in advance.


## Deployment overview

Use the following steps to deploy this solution on AWS. 

- Step 0: Deploy Stable Diffusion webUI (if you haven't deployed Stable Diffusion webUI before). 
- Step 1: Deploy the solution as middleware.
- Step 2: Configure API url and API token.
!!! Important "Notice" 
    This solution provides two usage options: through UI interface and by directly calling the backend API. Step 0 only needs to be executed if the user intends to use the UI interface. This step involves installing another open-source project Stable Diffusion webUI, allowing business operations to be conducted through the webUI.


## Deployment steps

### Step 0 - Linux: Deploy Stable Diffusion WebUI (Linux).

1. Sign in to the [AWS Management Console](https://console.aws.amazon.com/) and use [WebUI on EC2](https://console.aws.amazon.com/cloudformation/home?#/stacks/create/template?stackName=stable-diffusion-aws&templateURL=https://aws-gcr-solutions-us-east-1.s3.amazonaws.com/extension-for-stable-diffusion-on-aws/ec2.yaml){:target="_blank"} to create the stack.
2. On the **Create Stack** page, choose **Next**.
3. On the **Specify stack details** page, type a stack name in the Stack name box, adjust parameters as need, then choose **Next**.
4. On the **Configure stack options** page, choose **Next**.
5. On the **Review** page, review the details of your stack, check capabilities as required, and choose **Submit**.
6. Wait until the stack is created.
7. Find the output value of the CloudFormation stack, and navigate to the WebUI by clicking the link in the **WebUIURL** value, note you need to wait an extra 30 minutes to wait for the internal setup complete after the stack been created successfully.

### Step 0 - Windows: Deploy Stable Diffusion WebUI (Windows).
1. Start a Windows Server and log in via RDP.
2. Refer to [this link](https://docs.aws.amazon.com/en_us/AWSEC2/latest/WindowsGuide/install-nvidia-driver.html) to install the NVIDIA driver.
3. Visit the [Python website](https://www.python.org/downloads/release/python-3106/), download Python, and install it. Remember to check "Add Python to Path" during installation.
4. Visit the [Git website](https://git-scm.com/download/win), download Git, and install it.
5. Open PowerShell and download the source code of this project by executing: `git clone https://github.com/awslabs/stable-diffusion-aws-extension`.
6. Inside the source code directory, run `install.bat`.
7. In the downloaded `stable-diffusion-webui` folder, run `webui-user.bat`.


### Step 1: Deploy the solution as a middleware.
This automated AWS CloudFormation template deploys the solution in the AWS Cloud.

1. Sign in to the [AWS Management Console](https://console.aws.amazon.com/) and use [Launch solution in AWS Standard Regions](https://console.aws.amazon.com/cloudformation/home?#/stacks/create/template?stackName=stable-diffusion-aws&templateURL=https://aws-gcr-solutions.s3.amazonaws.com/stable-diffusion-aws-extension-github-mainline/latest/custom-domain/Extension-for-Stable-Diffusion-on-AWS.template.json){:target="_blank"} to launch the AWS CloudFormation template.   
2. The template will launch in the default region when you log into the console by default. To launch this solution in a different AWS Region, use the Region selector in the console navigation bar.
3. On the **Create stack** page, verify that the correct template URL is shown in the **Amazon S3 URL** text box and choose **Next**.

4. On the **Specify stack details** page, assign a valid and account level unique name to your solution stack. 
5. On the **Parameters** page, enter a new valid bucket name under **Bucket** for this solution to use, which is mainly for uploading dates and storing results. Enter a correct email address under **email** for future notice receiving. Select desired Amazon log level to be printed under **LogLevel**, only ERROR log will be printed by default. Enter a string of 20 characters that includes a combination of alphanumeric characters for **SdExtensionApiKey**, and it will be 09876543210987654321 by default, etc. Choose **Next**.
6. On the **Configure stack options** page, choose **Next**.
7. On the **Review** page, review and confirm the settings. Check the box acknowledging that the template will create AWS Identity and Access Management (IAM) resources. Choose **Create stack** to deploy the stack.

You can view the status of the stack in the AWS CloudFormation Console in the **Status** column. You should receive a CREATE_COMPLETE status in approximately 15 minutes.


!!! Important "Notice" 
    Please check the inbox of the email address you previously set up and click on the "Confirm subscription" hyperlink in the email with the subject "AWS Notification - Subscription Confirmation" to complete the subscription, and the message of 'Subscription confirmed!' appears.


### Step2: Configure API url and API token.
After successfully stack creation, you can refer to [here](../user-guide/multi-user.md) for subsequent configuration work.


<!-- 1. Go to [CloudFormation console](https://console.aws.amazon.com/cloudformation/).

2. Select the root stack of the solution from the stack list, instead of a nested stack. Nested stacks in the list will be labeled as (NESTED) next to their names.

3. Open the **Outputs** tab and locate the values corresponding to **APIGatewayUrl** and **ApiGatewayUrlToken**, and copy them.

4. Open the **Amazon SageMaker** tab in the Stable Diffusion WebUI. Paste the URL obtained in step 3 into the **API URL** text box. Enter the token obtained in step 3 into the **API Token** field. Click **Test Connection** to receive a confirmation message of **Successfully Connected**.

5. Click **Update Setting** to update the configuration file, so that you can receive the corresponding information next time. -->

<!-- ## Future step
After successful stack creation, you can find relevant information in the **Outputs** tab of AWS CloudFormation. -->

