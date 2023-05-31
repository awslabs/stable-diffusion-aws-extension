Before you launch the solution, review the architecture, supported regions, and other considerations discussed in this guide. Follow the step-by-step instructions in this section to configure and deploy the solution into your account.

**Time to deploy**: Approximately 15 minutes

## Prerequisition
User needs to install [Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) in advance.



## Deployment overview

Use the following steps to deploy this solution on AWS. 

- Step 1: Launch the AWS CloudFormation template into your AWS account.
- Step 2: Install 'Stable Diffusion AWS Extension' extension in your Stable Diffusion WebUI. 


## Deployment steps

### Step 1: Launch the AWS CloudFormation template into your AWS account.
This automated AWS CloudFormation template deploys the solution in the AWS Cloud.

1. Sign in to the AWS Management Console and use [Launch solution in AWS Standard Regions](https://console.aws.amazon.com/cloudformation/home?#/stacks/create/template?stackName=stable-diffusion-aws&templateURL=https://aws-gcr-solutions.s3.amazonaws.com/stable-diffusion-aws-extension-github-mainline/latest/custom-domain/Stable-diffusion-aws-extension-middleware-stack.template.json) to launch the AWS CloudFormation template.   
2. The template will launch in the default region when you log into the console by default. To launch this solution in a different AWS Region, use the Region selector in the console navigation bar.
3. On the **Create stack** page, verify that the correct template URL is shown in the **Amazon S3 URL** text box and choose **Next**.
4. On the **Specify stack details** page, assign a valid and account level unique name to your solution stack. Under **Parameters**, enter a valid bucket name under **aigcbucketname** for this solution to use, which is mainly for uploading dates and storing results. Enter a correct email address under **email** for future notice receiving. Enter a string of 20 characters that includes a combination of alphanumeric characters for **sdextensionapikey**, and it will be 09876543210987654321 by default. Select an instance type of Amazon EC2, which will mainly be used for operation including model creation, checkpoint merge, and etc. Choose **Next**.

    !!! Important "Notice" 
        Please check the inbox of the email address you previously set up and click on the "Confirm subscription" hyperlink in the email with the subject "AWS Notification - Subscription Confirmation" to complete the subscription, and the message of 'Subscription confirmed!' appears.

5. On the **Configure stack options** page, choose **Next**.
6. On the **Review** page, review and confirm the settings. Check the box acknowledging that the template will create AWS Identity and Access Management (IAM) resources. Choose **Create stack** to deploy the stack.

You can view the status of the stack in the AWS CloudFormation Console in the **Status** column. You should receive a CREATE_COMPLETE status in approximately 15 minutes.

### Step 2: Install 'Stable Diffusion AWS Extension' extension in your Stable Diffusion WebUI. 
1. Open the Stable Diffusion WebUI, navigate to the **Extensions** tab - **Install from URL** subtab, and enter the repository address of this solution [https://github.com/awslabs/stable-diffusion-aws-extension.git](https://github.com/awslabs/stable-diffusion-aws-extension.git) in the **URL from extension's git repository** text box. Click **Install**.
2. Navigate to **Installed** subtab, click **Apply and restart UI**. The **Amazon SageMaker** tab will appear in the WebUI, indicating that the extension installation has been completed.


## Future step
After successful stack creation, you can find relevant information in the **Outputs** tab of AWS CloudFormation.

