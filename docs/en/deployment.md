Before you launch the solution, review the architecture, supported regions, and other considerations discussed in this guide. Follow the step-by-step instructions in this section to configure and deploy the solution into your account.

**Time to deploy**: Approximately [10] minutes

## Prerequsite

Users need to prepare a computer running linux system in advance 

## Deployment overview

Use the following steps to deploy this solution on AWS. 

- Step1: Launch the Amazon CloudFormation template in your AWS account.
- Step2: Install the plugin Stable Diffusion AWS Extension via the install script.

## Deployment steps

This automated AWS CloudFormation template deploys the solution in the AWS Cloud.

1. Sign in to the AWS Management Console and use [Launch solution in AWS Standard Regions][launch-template] to launch the AWS CloudFormation template.   
2. By default, the template will launch in the default locale after you log into the console. To launch the solution in a specific Amazon Web Service region, select it from the Region drop-down list in the console navigation bar.
3. On the **Create stack** page, verify that the correct template URL is shown in the **Amazon S3 URL** text box and choose **Next**.
4. On the **Specify stack details** page, assign a name that is unique within the account and meets the naming requirements for your solution stack. In the **Parameters** section, enter a valid email address in **email** to receive future notifications. In the **sdextensionapikey** field, please enter a 20-character string containing a combination of numbers and letters; if not provided, the default is "09876543210987654321". Select the Amazon EC2 instance type in **utilscpuinsttype**, which is mainly used for operations including model creation and model merging. Click **Next**.
5. On the **Configure Stack Options** page, choose **Next**.
6. On the **Previe** page, review and confirm the settings. Make sure to select the checkbox confirming that the template will create Amazon Identity and Access Management (IAM) resources. And make sure to check the boxes for other features required by AWS CloudFormation. Select **Submit** to deploy the stack.
7. Wait until the status of the main stack changes to **CREATE_COMPLETE**, please record **ApiGatewayUrl** in the **Outpts** section
and **ApiGateWayUrlToken**

!!! Important "Hint"
    Please check the inbox of your reserved mailbox in time, and in the email with the subject "AWS Notification - Subscription Confirmation", click the "Confirm subscription" hyperlink and follow the prompts to complete the subscription.


