# Stable Diffusion AWS Extension
This is a WebUI extension to help user migrate existing workload (inference, train, ckpt merge etc.) from local server or standalone server to AWS Cloud.

## Why we build such extension
Stable Diffusion WebUI is a popular open-source GitHub project that provides an intuitive and user-friendly interface for data scientists and developers to interact with pre-trained txt2txt/img2img model, e.g. Dreambooth. The project has gained traction in the community (forks/stars/prs) for its ability to streamline the process of training, evaluating, and deploying models. As the demand for scalable and efficient machine learning solutions continues to rise, the Stable Diffusion WebUI project has emerged as a go-to tool for many user.
Some user existing workflow is shown below that the data scientists had to jump from customized WebUI, EC2 and manual scripts to accomplished a single model finetune process, which are:
* time consuming: the model training is executed on a standalone server that leading long training time (30-40 minutes per model) and no scalable workaround;
* error prone: data training, model (CKPT) packaging, endpoint deployment, UI update, result validation are not in a single panel;
* easily out-dated: functional feature of WebUI and community extension keep evolving, making existing customized WebUI laborious to sync with upstream community;

![Screen Shot 2023-05-20 at 21 44 58](https://github.com/aws-samples/stable-diffusion-aws-extension/assets/23544182/08109af4-84b0-4055-bf19-b9e8344dba75)

Thus we plan to contribute a solution aiming to mitigate above issue and provide a lite, decouple and user friendly AWS SageMaker based extension, in response to this growing demand and specific user requirement. We intergrate WebUI with AWS SageMaker, a fully managed service that allows users to build, train, and deploy machine learning models in the cloud. This extension will enable users to leverage the power of AWS SageMaker as the backend for model training and inference. With the AWS customized extension in place, Stable Diffusion WebUI will offer its users a more streamlined and cost-effective solution to optimize their existing workflows, including model training/finetune, inference and iteration with fast community pace.

## What is the user tuturial
We have provided a Stable Diffusion WebUI extension and AWS middleware for user, and user will install such extension by importing provided GitHub URL and AWS middleware by launch offered CloudFormation template in AWS console.
Brief user tutorial will be: User will first install the extension, extra tab will be installed for user to manager AWS credential, building AWS native SD model etc. then user will navigate to original txt2img tab, configure setting like CFG scale, batch count/size etc., then click 'Generate on Cloud' button to get the generated image. Thus providing user another alternative to utilize cloud resource without break existing user experience. Please refer to [user guide](https://aws-samples.github.io/stable-diffusion-aws-extension/en/) for more details.
![UIProcess](https://github.com/aws-samples/stable-diffusion-aws-extension/assets/23544182/3c6961d0-e1f9-4bee-b370-892978063781)

## What is the overall architecture & workflow
Diagram below is the brief view of internal workflow between our extension and middleware, user will keep launching community WebUI onto standalone EC2/local server with our extension installed, while the training and inference part will be pass onto AWS cloud (SageMaker, S3 etc.) through the RESTful API provided by middleware installed on user’s AWS account. Note the middleware is per AWS account, means it could be installed separately as work node to communicate with WebUI as control node, user only need to input endpoint URL and API key per account to decide which specific AWS account will be used for successive jobs.

![workflow](https://github.com/aws-samples/stable-diffusion-aws-extension/assets/23544182/2781734c-d1fb-44c3-bc57-c0e78e128c4e)

The major function of middleware is to provide RESTful API for WebUI extension to interact with AWS cloud resource (SageMaker, S3 etc.) with OpenAPI conformant schema, it will handling the request authentication, request dispatch to specific SageMaker/S3 API (SageMaker.jumpstart/model/predictor/estimator/tuner/utils etc.) and model lifecycle.
Diagram below is the overall architecture of middleware, including API Gateway and Lambda to fulfill the RESTful API function and Step Function to orchestrate the model lifecycle.

![middleware](https://github.com/aws-samples/stable-diffusion-aws-extension/assets/23544182/50a869a2-6c4c-4d43-9c1c-596bd50c54d6)

## How to get started
Please refer to [user guide](https://aws-samples.github.io/stable-diffusion-aws-extension/en/) to get started.

## Version
Alpha



