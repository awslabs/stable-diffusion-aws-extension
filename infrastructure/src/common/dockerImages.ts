import { ECR_IMAGE_TAG } from "./dockerImageTag";

export const AIGC_WEBUI_INFERENCE: string = 'public.ecr.aws/aws-gcr-solutions/stable-diffusion-aws-extension/aigc-webui-inference:' + ECR_IMAGE_TAG;
export const AIGC_WEBUI_UTILS: string = 'public.ecr.aws/aws-gcr-solutions/stable-diffusion-aws-extension/aigc-webui-utils:' + ECR_IMAGE_TAG;
export const AIGC_WEBUI_DREAMBOOTH_TRAINING: string = 'public.ecr.aws/aws-gcr-solutions/stable-diffusion-aws-extension/aigc-webui-dreambooth-training:' + ECR_IMAGE_TAG;
