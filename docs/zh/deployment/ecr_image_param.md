# 如何修改方案使用的ECR镜像tag
当前项目使用了如下三个Public ECR的镜像用于training和inference:
* public.ecr.aws/aws-gcr-solutions/stable-diffusion-aws-extension/aigc-webui-inference: TAG_NAME
* public.ecr.aws/aws-gcr-solutions/stable-diffusion-aws-extension/aigc-webui-utils: TAG_NAME
* public.ecr.aws/aws-gcr-solutions/stable-diffusion-aws-extension/aigc-webui-dreambooth-training: TAG_NAME

对应的部署CDK代码位于
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
TAG_NAME是由Cloudformation的部署参数ecrimagetag来定义，默认tag的值是方案发布CICD的pipeline每次编译的时候动态生成，比如‘v1.0.0-46f9d43’, 其中v1.0.0是方案的大版本tag，46f9d43是项目github的commit id。

绝大部分情况用户不需要修改这个ECR的tag名字，用户如果需要修改这个tag值，需要在部署方案cloudformation的时候修改默认的参数值，到目前为止，我们有两个tag值供用户选择:
1. v1.0.0
2. v1.0.1-COMMITID