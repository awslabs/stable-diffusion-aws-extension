Before deploying the solution, it is recommended that you first review information in this guide regarding architecture diagrams and regional support. Then, follow the instructions below to configure the solution and deploy it to your account.

Deployment time: arount 20 minutes.

## Deployment Summary
Deploying this solution (ComfyUI portion) on Amazon Web Services primarily involves the following processes:

- Step 1: Deploy the middleware of the solution.
- Step 2: Deploy ComfyUI frontend.

After the successfully deployment, please refer to [ComfyUI User Guide](../user-guide/ComfyUI/inference.md) for more details.



## Deployment Steps
### Step 1: Deploy the middleware of the solution
This automated Amazon CloudFormation template deploys the solution in Amazon Web Services.

1. Sign in to the [AWS Management Console](https://console.aws.amazon.com/)，and use [Extension for Stable Diffusion on AWS](https://console.aws.amazon.com/cloudformation/home?#/stacks/create/template?stackName=stable-diffusion-aws&templateURL=https://aws-gcr-solutions.s3.amazonaws.com/stable-diffusion-aws-extension-github-mainline/latest/custom-domain/Extension-for-Stable-Diffusion-on-AWS.template.json){:target="_blank"} to create the stack.
2. By default, this template will launch in the default region after you log in to the console. To launch this solution in a specified Amazon Web Services region, please select the desired region from the region drop-down list in the console's navigation bar.
3. In the **Create Stack** page，confirm that the correct template URL has been entered in the **Amazon S3 URL** text box, then select **Next**.
4. In the **Specify stack details** page, assign a unique name within your account that meets the naming requirements for your solution stack. Refer to the table below for deployment parameters. Click **Next**.

    |Parameter|Description|Recommendation|
    |:-------------|:--------------|:--------------|
    |APIEndpointType|For API calls, define the category of the API. The options are REGIONAL, PRIVATE, EDGE| Regional by default|
    |Bucket|Enter a valid new S3 bucket name (or the name of a previously deployed S3 bucket used for the ComfyUI section of this solution)||
    |email|Enter a valid email address for further notification receivement||
    |SdExtensionApiKey|Please enter a 20-character string that includes a combination of numbers and letters |"09876543210987654321" by default|
    |LogLevel| Please select a desired Lambda Log leval| Only ERROR logs will be printed by default|

5. In the **Configure stack options** page, select **Next**. 
6. In the **Review** page, review and confirm the settings. Ensure that the checkbox for confirming that the template will create Amazon Identity and Access Management (IAM) resources is selected. Also, make sure to select the checkboxes for any other AWS CloudFormation-required features. Choose **Submit** to deploy the stack.
7. You can check the **status** of the stack in the Status column of the AWS CloudFormation console. You should receive a **CREATE_COMPLETE** status within approximately 15 minutes.

    !!! tip
        Please check your reserved email inbox promptly and click the "Confirm subscription" hyperlink in the email with the subject "AWS Notification - Subscription Confirmation" to complete the subscription as instructed.


### Step 2: Deploy ComfyUI frontend
This step will install the ComfyUI frontend for the customer. This frontend automatically includes Chinese language plugins and buttons for publishing workflows to the cloud, providing a more user-friendly UI interaction. This automated Amazon CloudFormation template is deployed within Amazon Web Services (AWS).

1. Sign in to the [AWS Management Console](https://console.aws.amazon.com/), click **Create Stack** in the upper right, **With new resource(standard)** to launch the AWS CloudFormation template.
2. In the page of **Create Stack**, select **Choose an existing template**，**Specify template** field **Amazon S3 URLe**, enter [Amazon S3 URL](https://aws-gcr-solutions.s3.amazonaws.com/extension-for-stable-diffusion-on-aws/comfy.yaml)，and click **Next**。
3. In the page of **Specify stack details**，assign a unique and name-compliant name for your solution stack within your account. In the Parameters section, the deployment parameter descriptions are as follows. Click **Next**。

    !!! tip 
        The EC2 Key Pair here is primarily used for remote connections to EC2 instances from your local machine. If you don’t have an existing one, you can refer to [Create Key Pairs](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/create-key-pairs.html){:target="_blank"}.

    |Parameter |Description|Recommendation|
    |:-------------|:--------------|:--------------|
    |InstanceType |Instance type of EC2 | For tasks involving inference animations, videos, etc., it is recommended to use G6 or G5 instances |
    |NumberOfInferencePorts|Number of inference interface|It is recommended not to exceed 5|
    |StackName| Stack Name from the successfully deployed stack in Step 1 of the deployment process||
    |keyPairName|Select a desired existing EC2 Key Pair||

4. In the page of **Configure stack options**, select **Next**。
5. In the **Review** page, review and confirm the settings. Ensure that the checkbox for confirming that the template will create Amazon Identity and Access Management (IAM) resources is selected. Also, make sure to select the checkboxes for any other AWS CloudFormation-required features. Choose **Submit** to deploy the stack.
6. You can check the **status** of the stack in the Status column of the AWS CloudFormation console. You should receive a **CREATE_COMPLETE** status within approximately 3 minutes.
7. Select the successfully deployed stack, open **Outputs**, and click the link corresponding to **Designer** to open the ComfyUI front-end of the solution deployment. Access to Designer may require disabling the VPN or removing port 10000. **NumberOfInferencePortsStart** represents the starting port for the inference environment address, and the port addresses increase sequentially according to the deployment quantity. For example, when NumberOfInferencePorts is set to 2, the address range and the accessible inference environment addresses are sequentially as follows:"http://EC2地址:10001，http://EC2地址:10002.

    |Role|Functions|Ports|
    |:-------------|:--------------|:--------------|
    |Senior Artist/ Staff of workflow management| Able to install new custom nodes, debug workflows on EC2, and deploy workflows and environments to Amazon SageMaker. You can also call SageMaker resources and select published workflows for inference validation | http://EC2 Address|
    |Junior Artists| From the interface accessed through this port, you can select the workflows published by the Art Director, simply modify the inference parameters, check 'Prompt on AWS', and then call Amazon SageMaker for inference. When NumberOfInferencePorts is set to 3, the address range and accessible inference environment addresses are sequentially as follows:"：<ul><li>http://EC2Address:10001 </li><li>http://EC2Address:10002 </li><li>http://EC2Address:10003</li></ul>|

    !!! tip 
        After the initial deployment, you need to wait for a while. If you open the link and see the message 'Comfy is Initializing or Starting,' it means that the backend is in the process of initializing ComfyUI. Please wait a bit and then refresh the page to confirm.









