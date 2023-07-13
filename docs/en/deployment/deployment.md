Before you launch the solution, review the architecture, supported regions, and other considerations discussed in this guide. Follow the step-by-step instructions in this section to configure and deploy the solution into your account.

**Time to deploy**: Approximately 25 minutes.

## Prerequisition
Users need to prepare a computer running linux system in advance.


## Deployment overview

Use the following steps to deploy this solution on AWS. 

- Step 1: Deploy Stable Diffusion WebUI. 
- Step 2: Deploy the solution as a middleware.
- Step 3: Configure API url and API token.



## Deployment steps

### Step 1: Deploy Stable Diffusion WebUI.

1. Download the CloudFormation Template from [link](https://raw.githubusercontent.com/awslabs/stable-diffusion-aws-extension/main/workshop/ec2.yaml)

2. Sign in to the [AWS Management Console](https://console.aws.amazon.com/) and go to [CloudFormation console](https://console.aws.amazon.com/cloudformation/)

3. On the Stacks page, choose **Create stack**, and then choose **With new resources (standard)**.

4. On the **Specify template** page, choose **Template is ready**, choose **Upload a template file**, and then browse for the template that is downloaded in step 1, and then choose **Next**.

5. On the **Specify stack details** page, type a stack name in the Stack name box. Choose an EC2 instance key pair, then choose **Next**.

6. On the **Configure stack options** page, choose **Next**.

7. On the **Review** page, review the details of your stack, and choose **Submit**.

8. Wait until the stack is created.

9. Find the output value of the CloudFormation stack, and navigate to the WebUI by clicking the link in the **WebUIURL** value, note you need to wait extra 5 minutes to wait for the internal setup complete after the stack been created successfully.


### Step 2: Deploy the solution as a middleware.
This automated AWS CloudFormation template deploys the solution in the AWS Cloud.

1. Sign in to the [AWS Management Console](https://console.aws.amazon.com/) and use [Launch solution in AWS Standard Regions](https://console.aws.amazon.com/cloudformation/home?#/stacks/create/template?stackName=stable-diffusion-aws&templateURL=https://aws-gcr-solutions.s3.amazonaws.com/stable-diffusion-aws-extension-github-mainline/latest/custom-domain/Stable-diffusion-aws-extension-middleware-stack.template.json){:target="_blank"} to launch the AWS CloudFormation template.   
2. The template will launch in the default region when you log into the console by default. To launch this solution in a different AWS Region, use the Region selector in the console navigation bar.
3. On the **Create stack** page, verify that the correct template URL is shown in the **Amazon S3 URL** text box and choose **Next**.
4. On the **Specify stack details** page, assign a valid and account level unique name to your solution stack. Under **Parameters**, enter a valid bucket name under **aigcbucketname** for this solution to use, which is mainly for uploading dates and storing results. Enter a correct email address under **email** for future notice receiving. Enter a string of 20 characters that includes a combination of alphanumeric characters for **sdextensionapikey**, and it will be 09876543210987654321 by default. Select an instance type of Amazon EC2, which will mainly be used for operation including model creation, checkpoint merge, and etc. Choose **Next**.


5. On the **Configure stack options** page, choose **Next**.
6. On the **Review** page, review and confirm the settings. Check the box acknowledging that the template will create AWS Identity and Access Management (IAM) resources. Choose **Create stack** to deploy the stack.

You can view the status of the stack in the AWS CloudFormation Console in the **Status** column. You should receive a CREATE_COMPLETE status in approximately 15 minutes.


!!! Important "Notice" 
    Please check the inbox of the email address you previously set up and click on the "Confirm subscription" hyperlink in the email with the subject "AWS Notification - Subscription Confirmation" to complete the subscription, and the message of 'Subscription confirmed!' appears.


### Step3: Configure API url and API token.

1. Go to [CloudFormation console](https://console.aws.amazon.com/cloudformation/).

2. Select the root stack of the solution from the stack list, instead of a nested stack. Nested stacks in the list will be labeled as (NESTED) next to their names.

3. Open the **Outputs** tab and locate the values corresponding to **APIGatewayUrl** and **ApiGatewayUrlToken**, and copy them.

4. Open the **Amazon SageMaker** tab in the Stable Diffusion WebUI. Paste the URL obtained in step 3 into the **API URL** text box. Enter the token obtained in step 3 into the **API Token** field. Click **Test Connection** to receive a confirmation message of **Successfully Connected**.

5. Click **Update Setting** to update the configuration file, so that you can receive the corresponding information next time.


<!-- ### Step 2: Install the Extension for Stable Diffusion on AWS through the installation script.
1. In the working directory of the computer running linux prepared in advance, run the following command to download the latest installation script
```
wget https://raw.githubusercontent.com/awslabs/stable-diffusion-aws-extension/main/install.sh
```
2. Run the installation script
```
sh install.sh
```
3. Move to the stable-diffusion-webui folder downloaded by install.sh
```
cd stable-diffusion-webui
```
4. For machines without GPU, you can start the webui with the following command
```
./webui.sh --skip-torch-cuda-test
```
5. For machines with GPU, you can start the webui with the following command
```
./webui.sh
``` -->
<!-- 
### Step 2: Install 'Stable Diffusion AWS Extension' extension in your Stable Diffusion WebUI. 
1. Open the Stable Diffusion WebUI, navigate to the **Extensions** tab - **Install from URL** subtab, and enter the repository address of this solution [https://github.com/awslabs/stable-diffusion-aws-extension.git](https://github.com/awslabs/stable-diffusion-aws-extension.git) in the **URL from extension's git repository** text box. Click **Install**.
2. Navigate to **Installed** subtab, click **Apply and restart UI**. The **Amazon SageMaker** tab will appear in the WebUI, indicating that the extension installation has been completed. -->
<!-- ## Future step
After successful stack creation, you can find relevant information in the **Outputs** tab of AWS CloudFormation. -->

