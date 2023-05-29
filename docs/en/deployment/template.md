To automate deployment, this solution uses the following AWS CloudFormation templates, which you can download before deployment:

 [Stable Diffusion Extension on AWS](https://console.aws.amazon.com/cloudformation/home?#/stacks/create/template?stackName=stable-diffusion-aws&templateURL=https://aws-gcr-solutions.s3.amazonaws.com/stable-diffusion-aws-extension-github-mainline/latest/custom-domain/Stable-diffusion-aws-extension-middleware-stack.template.json): Use this template to launch the solution and all associated components. The default configuration deploys [Amazon API Gateway][api-gateway], [Amazon Lambda][lambda], [Amazon S3][s3], [Amazon EFS][efs] and [Amazon Batch][Batch], but you can customize the template to meet your specific needs.

