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
    |SdExtensionApiKey|Please enter a 20-character string consisting of numbers and letters|Default is "09876543210987654321"|
    |LogLevel|Choose the Lambda Log printing level you prefer|Default is ERROR only printed|

5. On the **Specify Stack Options** page, choose **Next**.
6. On the **Review** page, review and confirm the settings. Make sure the checkbox to acknowledge that the template will create AWS Identity and Access Management (IAM) resources is selected. Also, make sure the checkbox for other capabilities required by AWS CloudFormation is selected. Choose **Submit** to deploy the stack.
7. You can view the status of the stack in the **Status** column of the AWS CloudFormation console. You should receive a **CREATE_COMPLETE** status in approximately 15 minutes.

    !!! tip "Tip"
        Please check your reserved email inbox promptly and click the "Confirm subscription" link in the email with the subject "AWS Notification - Subscription Confirmation" to complete the subscription as prompted.


### Step 2: Deploy the ComfyUI Frontend
Step 2 will install the ComfyUI frontend for the customer. This frontend automatically includes a Chinese localization plugin and buttons for publishing workflows to the cloud, providing a more user-friendly UI interface for customers. This automated Amazon CloudFormation template is deployed in Amazon Web Services.

1. Log in to the [AWS Management Console](https://console.aws.amazon.com/), click **Create Stack** in the top right corner of the console, **With new resource (standard)**, and the page will redirect to create a stack.
2. On the **Create Stack** page, select **Choose an existing template**, in the **Specify template** area, select **Amazon S3 URL**, enter this [deployment template link](https://aws-gcr-solutions.s3.amazonaws.com/extension-for-stable-diffusion-on-aws/comfy.yaml), and then select **Next**.
3. On the **Specify Stack Details** page, assign a unique name within your account that complies with the naming requirements for your solution stack. In the **Parameters** section, the deployment parameter descriptions are as follows. Click **Next**.

    !!! tip "Tip"
        The EC2 Key Pair here is mainly used for local remote connection to EC2. If you don't have an existing one, you can refer to the [official manual](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/create-key-pairs.html){:target="_blank"} to create one.

    |Parameter|Description|Recommendation|
    |:-------------|:--------------|:--------------|
    |InstanceType |Instance type of the deployed EC2| If it involves inferencing animations, videos, etc., G6, G5 instances are recommended|
    |NumberOfInferencePorts|Number of inference environments|Recommended not to exceed 5|
    |StackName|Name of the stack successfully deployed from Step 1||
    |keyPairName|Select an existing EC2 Key Pair||

4. On the **Configure Stack Options** page, select **Next**.
5. On the **Review** page, review and confirm the settings. Make sure to check the box acknowledging that the template will create Amazon Identity and Access Management (IAM) resources. Also, make sure to check the box for AWS CloudFormation to perform the other capabilities required. Select **Submit** to deploy the stack.
6. You can view the stack status in the **Status** column of the AWS CloudFormation console. You should receive a **CREATE_COMPLETE** status within approximately 3 minutes.
7. Select the successfully deployed stack, open **Outputs**, and click the link corresponding to **Designer** to open the ComfyUI frontend deployed by the solution. Accessing the Designer may require disabling the VPN or removing port 10000. **NumberOfInferencePortsStart** represents the starting port address of the inference environment, with the port addresses incrementing according to the number of deployments. For example, if NumberOfInferencePorts is set to 2, the accessible inference environment addresses are: http://EC2Address:10001, http://EC2Address:10002.

    |Role|Function|Port|
    |:-------------|:--------------|:--------------|
    |Lead Artist/Workflow Manager| Can install new custom nodes, debug workflows on EC2, publish workflows and environments to Amazon SageMaker. Can also call SageMaker resources, select published workflows for inference validation.| http://EC2Address|
    |Regular Artist| From this port, the interface can select workflows published by the lead artist, modify inference parameters, check "Prompt on AWS", and call Amazon SageMaker for inference.|If NumberOfInferencePorts is set to 3, the range of accessible inference environment addresses is: <ul><li>http://EC2Address:10001</li><li>http://EC2Address:10002</li><li>http://EC2Address:10003</li></ul>|

    !!! tip "Tip"
        After the initial deployment, you may need to wait a bit. If you see a prompt saying "Comfy is Initializing or Starting" when opening the link, it means the backend is initializing ComfyUI. Please wait a moment and refresh the page again to confirm.


### Step 3: Debug and create a usable workflow on the ComfyUI page.
You can refer to the "Debugging Workflows" subsection in [this guide](../user-guide/ComfyUI/inference.md)

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






