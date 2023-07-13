# How to modify the ECR image tag used in the solution

The current project uses the following three Public ECR images for training and inference:
- public.ecr.aws/aws-gcr-solutions/stable-diffusion-aws-extension/aigc-webui-inference: TAG_NAME
- public.ecr.aws/aws-gcr-solutions/stable-diffusion-aws-extension/aigc-webui-utils: TAG_NAME
- public.ecr.aws/aws-gcr-solutions/stable-diffusion-aws-extension/aigc-webui-dreambooth-training: TAG_NAME

The corresponding CDK deployment code can be found in:
1. infrastructure/src/common/dockerImages.ts

```typescript
export const AIGC_WEBUI_INFERENCE: string = 'public.ecr.aws/aws-gcr-solutions/stable-diffusion-aws-extension/aigc-webui-inference:';
export const AIGC_WEBUI_UTILS: string = 'public.ecr.aws/aws-gcr-solutions/stable-diffusion-aws-extension/aigc-webui-utils:';
export const AIGC_WEBUI_DREAMBOOTH_TRAINING: string = 'public.ecr.aws/aws-gcr-solutions/stable-diffusion-aws-extension/aigc-webui-dreambooth-training:';
```

2. infrastructure/src/common/dockerImageTag.ts

```typescript
export const ECR_IMAGE_TAG: string = 'dev';
```

TAG_NAME is defined by the CloudFormation deployment parameter `ecrimagetag`. By default, the tag value is dynamically generated during each compilation of the solution's CICD pipeline. For example, 'v1.0.0-46f9d43', where 'v1.0.0' represents the major version tag of the solution, and '46f9d43' is the commit ID of the project on GitHub.

In most cases, users do not need to modify the ECR tag name. However, if users need to change the tag value, they can modify the default parameter value during the deployment of the solution's CloudFormation stack. Currently, we have two tag values available for users to choose from:
1. v1.0.0
2. v1.0.1-COMMITID

```
