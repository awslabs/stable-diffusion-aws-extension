# AWS Extension for Stable Diffusion
This is a WebUI extension to help user migrate existing workload (inference, train, ckpt merge etc.) from local server or standalone server to AWS Cloud.

## How to get started:

>**Notice** : This extension currently only support stable-diffusion-webui running on **Linux** platform, we are still working on support other platforms in the near future.

### **Part1**: Install the stable-diffusion-webui and extension
#### **Option 1 (Recommended)**: Use one click AWS Cloudformation Template to install the EC2 instance with WebUI and extension
1. Install the EC2 by using [CloudFormation Template](https://raw.githubusercontent.com/awslabs/stable-diffusion-aws-extension/main/workshop/ec2.yaml) to install CloudFormation template directly
2. Select the EC2 instance key pair, and keep click with default operation to create the stack
3. Find the output value of the CloudFormation stack, and navigate to the WebUI by clicking the link in the WebUIURL value, note you need to wait extra 5 minutes to wait for the internal setup complete after the stack been created successfully.

#### **Option 2**: Use script if you already had a EC2 instance (Ubuntu 20.04 LTS recommended) without WebUI installed
1. In the working directory of a Linux computer prepared in advance, run the following command to download the latest installation script:
```bash
wget https://raw.githubusercontent.com/awslabs/stable-diffusion-aws-extension/main/install.sh
```
2. Run the installation script, this script will try to git clone following repos and put the extensions on stable-diffusion-webui extension directory:
   * stable-diffusion-webui
   * stable-diffusion-aws-extension
   * sd-webui-controlnet
   * sd_dreambooth_extension
```bash
sh install.sh
```
>**Notice** :The version of the downloaded repos has been set in the install.sh script, please do not manually change the version, we have tested on the version set in the script.
3. Move to the stable-diffusion-webui folder downloaded by install.sh:
```bash
cd stable-diffusion-webui
```
4. For machines without a GPU, you can start the web UI using the following command:
```bash
./webui.sh --skip-torch-cuda-test
```
5. For machines with a GPU, you can start the web UI using the following command:
```bash
./webui.sh
```

### **Part2**: Install Middleware On AWS Cloud
#### **Option 1**: Use AWS Cloudformation Template
1. Install the middleware by click the [**link to navigate to AWS CloudFormation console**](https://console.aws.amazon.com/cloudformation/home?#/stacks/create/template?stackName=stable-diffusion-aws&templateURL=https://aws-gcr-solutions.s3.amazonaws.com/stable-diffusion-aws-extension-github-mainline/latest/custom-domain/Stable-diffusion-aws-extension-middleware-stack.template.json) to install CloudFormation template directly, input the parameter accordingly, note the aigcbucketname is the bucket to store all your solution assets, email is the mail address you register to receive notification for events like model training complete, the apikey is the basic authentication for your api url connection, the trainmodelinferencetype is the ec2 instance type you choose to handle the workload like ckpt merge that can be handled by cpu enough.:

<img width="1377" alt="iShot_2023-06-01_14 52 51" src="https://github.com/awslabs/stable-diffusion-aws-extension/assets/2245949/3fe9469a-b9e1-4633-ac4d-ceb6a459fec5">

For users who need explicit IAM permissions for strict account control, we provide [CloudFormation template](https://github.com/awslabs/stable-diffusion-aws-extension/blob/dev/workshop/middleware-min-role.yaml) to help system administrators create IAM roles with minimal permissions, user can create & delete middleware CloudFormation templates through newly such created roles.

**Create new mininum role first, e.g. sd-min-role.**
![image](https://github.com/awslabs/stable-diffusion-aws-extension/assets/23544182/148841f6-8fad-4166-8f02-8a306b177459)

**Specify such role in Cloudformation creation.**
![image](https://github.com/awslabs/stable-diffusion-aws-extension/assets/23544182/3121c876-79d4-48a2-8260-be80c480b893)

>**Notice** : We prefer use deploy our solution in *us-east-1* region, the reason is that in other region there is an existing S3 CORS issue which will block user to upload inference config for arround 2 hours. That mean user need to wait arround 2 hours after deploy the middleware to do the inference job. We will keep monitoring the progress of this issue.

#### **Option 2**: Use AWS CDK(Cloud Development Kit)
**Prerequisite**
To set up the development environment, you will need have AWS account and tools with preferred version below to install from source code:
- NPM, Node
- [AWS CDK](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html#getting_started_install)
- Docker

1. Deploy the project to your AWS account (make sure your current profile has Administrator access, with AWS CDK, Docker installed):

   ```bash
   aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws
   cd infrastructure/
   npm install
   npx cdk bootstrap
   npx cdk deploy
   ```
   You can specify the following three parameters:
   * **sub-email-address**: your subscribe email to receive notification, the email will get endpoint deployment error
   * **api-token: your token** of api key for api authentication
   * **util-instance-type**: c2 instance type for operations including ckpt merge, model create etc. Candidate is [**ml.r5.large, ml.r5.xlarge, ml.c6i.2xlarge, ml.c6i.4xlarge,ml.r5.large**]
   ```
   npx cdk deploy --parameters api-token=<XXXXXXX>\
   --parameters sub-email-address=<YOUREMAIL@XXX.COM>\
   --parameters util-instance-type=<ml.r5.large | ml.r5.xlarge| ml.c6i.2xlarge | ml.c6i.4xlarge | ml.r5.large>
   ```
   The project build and deployment will take about 25 minutes and the first time can be longer due to container image packaging. Once the project deployed successfully to your AWS account, you will see output similar below:

   ```text
     Stable-diffusion-aws-extension-middleware-stack: creating CloudFormation changeset...

     ✅  Stable-diffusion-aws-extension-middleware-stack
    
     ✨  Deployment time: 218.39s
    
     Outputs:
     Stable-diffusion-aws-extension-middleware-stack.ApiGatewayUrl = {API_GATEWAY_URL}          // this url will needed later 
     Stable-diffusion-aws-extension-middleware-stack.S3BucketName = {YOUR_S3_BUCKET_LOCATION}
     Stable-diffusion-aws-extension-middleware-stack.SNSTopicName = {SNS_TOPIC}
     Stack ARN:
     arn:aws:cloudformation:us-east-1:{ACCOUNT_NUMBER}:stack/Stable-diffusion-aws-extension-middleware-stack/{ARN}
   ```
5. Go to AWS CloudFormation console, find the stack you just created, click "Outputs" tab, you will see the API Gateway URL, API Token. You will need them later.
![Screen Shot 2023-05-28 at 20 35 11](https://github.com/awslabs/stable-diffusion-aws-extension/assets/23544182/743312ea-2cc8-4a2b-bfb8-dcb60cb8862e)

## Set up the extension in WebUI console

1. Go back the WebUI console, and choose "AWS SageMaker" tab, enter the API Gateway URL and API token you just got from CloudFormation/CDK output, click "Update Setting" and "Test Connection" button to make sure the connection is successful. Or you can create new file called ```sagemaker_ui.json``` for the same purpose, the file should be placed under stable diffusion root folder and the content should be like below:
   
   ```json
   {
    "api_gateway_url": "{API_GATEWAY_URL}", 
    "api_token": "{API_GATEWAY_KEY}"  
   }

   ```

Please refer to [**user guide**](https://awslabs.github.io/stable-diffusion-aws-extension/zh/user-guide/preparation/) for following detailed operations.

## Why we build such extension
Stable Diffusion WebUI is a popular open-source GitHub project that provides an intuitive and user-friendly interface for data scientists and developers to interact with pre-trained txt2img/img2img model, e.g. Dreambooth. The project has gained traction in the community (forks/stars/prs) for its ability to streamline the process of training, evaluating, and deploying models. As the demand for scalable and efficient machine learning solutions continues to rise, the Stable Diffusion WebUI project has emerged as a go-to tool for many user.
Some user existing workflow is shown below that the data scientists had to jump from customized WebUI, EC2 and manual scripts to accomplished a single model finetune process, which are:
* time consuming: the model training is executed on a standalone server that leading long training time (30-40 minutes per model) and no scalable workaround;
* error prone: data training, model (CKPT) packaging, endpoint deployment, UI update, result validation are not in a single panel;
* easily out-dated: functional feature of WebUI and community extension keep evolving, making existing customized WebUI laborious to sync with upstream community;

![Screen Shot 2023-05-20 at 21 44 58](https://github.com/aws-samples/stable-diffusion-aws-extension/assets/23544182/08109af4-84b0-4055-bf19-b9e8344dba75)

Thus we plan to contribute a solution aiming to mitigate above issue and provide a lite, decouple and user friendly AWS SageMaker based extension, in response to this growing demand and specific user requirement. We intergrate WebUI with AWS SageMaker, a fully managed service that allows users to build, train, and deploy machine learning models in the cloud. This extension will enable users to leverage the power of AWS SageMaker as the backend for model training and inference. With the AWS customized extension in place, Stable Diffusion WebUI will offer its users a more streamlined and cost-effective solution to optimize their existing workflows, including model training/finetune, inference and iteration with fast community pace.

## What is the user tuturial
We have provided a Stable Diffusion WebUI extension and AWS middleware for user, and user will install such extension by importing provided GitHub URL and AWS middleware by launch offered CloudFormation template in AWS console.
Brief user tutorial will be: User will first install the extension, extra tab will be installed for user to manager AWS credential, building AWS native SD model etc. then user will navigate to original txt2img tab, configure setting like CFG scale, batch count/size etc., then click 'Generate on Cloud' button to get the generated image. Thus providing user another alternative to utilize cloud resource without break existing user experience. Please refer to [user guide](https://awslabs.github.io/stable-diffusion-aws-extension/en/) for more details.
![UIProcess](https://github.com/aws-samples/stable-diffusion-aws-extension/assets/23544182/3c6961d0-e1f9-4bee-b370-892978063781)

## What is the overall architecture & workflow
Diagram below is the brief view of internal workflow between our extension and middleware, user will keep launching community WebUI onto standalone EC2/local server with our extension installed, while the training and inference part will be pass onto AWS cloud (SageMaker, S3 etc.) through the RESTful API provided by middleware installed on user’s AWS account. Note the middleware is per AWS account, means it could be installed separately as work node to communicate with WebUI as control node, user only need to input endpoint URL and API key per account to decide which specific AWS account will be used for successive jobs.

![workflow](https://github.com/aws-samples/stable-diffusion-aws-extension/assets/23544182/2781734c-d1fb-44c3-bc57-c0e78e128c4e)

The major function of middleware is to provide RESTful API for WebUI extension to interact with AWS cloud resource (SageMaker, S3 etc.) with OpenAPI conformant schema, it will handling the request authentication, request dispatch to specific SageMaker/S3 API (SageMaker.jumpstart/model/predictor/estimator/tuner/utils etc.) and model lifecycle.
Diagram below is the overall architecture of middleware, including API Gateway and Lambda to fulfill the RESTful API function and Step Function to orchestrate the model lifecycle.

![middleware](https://github.com/awslabs/stable-diffusion-aws-extension/assets/23544182/8d871565-5792-4a7c-87c9-53fc66d96a5c)

- Users in the WebUI console will use the assigned API token to trigger a request to API Gateway while being authenticated. (Note: AWS credentials are not required in AWS WebUI)
- API Gateway will route requests to Lambda with different functions according to URL prefixes to implement corresponding tasks (for example, model uploading, checkpoint merging), model training, and model inference. At the same time, the Lambda function records operational metadata into DynamoDB (eg, inferred parameters, model name) for subsequent query and correlation.
- During the training process, the Step Function will be called to orchestrate the training process, which includes using Amazon SageMaker for training and SNS for training status notification. During the inference process, the Lambda function will call Amazon SageMaker for asynchronous inference. Training data, models and checkpoints will be stored in S3 buckets separated by different prefixes.

### Source Code Structure

```
.
├── CHANGELOG.md
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── LICENSE
├── NOTICE
├── README.md
├── THIRD-PARTY-LICENSES.txt
├── build_scripts -- scripts to build the docker images, we use these scripts to build docker images on cloud
├── buildspec.yml -- buildspec file for CodeBuild, we have code pipeline to use this buildspec to transfer the CDK assets to Cloudformation templates
├── deployment    -- scripts to deploy the CloudFormation template
├── docs
├── dreambooth_sagemaker -- SageMaker support for dreambooth
├── infrastructure -- CDK project to deploy the middleware, all the middle ware infrastructure code is in this directory
├── install.py -- install dependencies for the extension
├── install.sh --  script to set the webui and extension to specific version
├── javascript -- javascript code for the extension
├── middleware_api -- middleware api denifition and lambda code
├── pre-flight.sh -- version compatibility check & install
├── sagemaker_entrypoint_json.py -- wrapper function for SageMaker
├── scripts -- extension related code for WebUI
└── utils.py -- wrapper function for configure options
```

## Version
Beta

## Changelog
Alpha
- txt2img (ckpt merge, training, inference)
- dreambooth, controlnet plugin support
- compatible version (commit id), webui - "89f9faa6", controlnet - "7c674f83", dreambooth - "926ae204"




