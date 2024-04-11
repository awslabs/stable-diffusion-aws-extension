# ソリューションで使用される ECR イメージタグを変更する方法

現在のプロジェクトでは、トレーニングと推論に次の 3 つの Public ECR イメージを使用しています:
- public.ecr.aws/aws-gcr-solutions/stable-diffusion-aws-extension/aigc-webui-inference: TAG_NAME 
- public.ecr.aws/aws-gcr-solutions/stable-diffusion-aws-extension/aigc-webui-utils: TAG_NAME 
- public.ecr.aws/aws-gcr-solutions/stable-diffusion-aws-extension/aigc-webui-dreambooth-training: TAG_NAME 

対応する CDK デプロイメントコードは次のファイルにあります:
1. infrastructure/src/common/dockerImages.ts 

```typescript 
export const AIGC_WEBUI_INFERENCE: string = 'public.ecr.aws/aws-gcr-solutions/stable-diffusion-aws-extension/aigc-webui-inference:'; 
export const AIGC_WEBUI_DREAMBOOTH_TRAINING: string = 'public.ecr.aws/aws-gcr-solutions/stable-diffusion-aws-extension/aigc-webui-dreambooth-training:'; 
``` 

2. infrastructure/src/shared/const.ts 

```typescript 
export const ECR_IMAGE_TAG: string = 'dev'; 
``` 

TAG_NAME は CloudFormation デプロイメントパラメータ `EcrImageTag` で定義されています。デフォルトでは、タグ値はソリューションの CICD パイプラインの各コンパイル時に動的に生成されます。例えば、 'v1.0.0-46f9d43' では、 'v1.0.0' はソリューションのメジャーバージョンタグ、 '46f9d43' は GitHub のプロジェクトのコミット ID です。

ほとんどの場合、ユーザーは ECR タグ名を変更する必要はありません。ただし、ユーザーがタグ値を変更する必要がある場合は、ソリューションの CloudFormation スタックのデプロイ時にデフォルトのパラメータ値を変更できます。現在、ユーザーが選択できるタグ値は次の 2 つです:
1. v1.0.0 
2. v1.0.1-COMMITID 
