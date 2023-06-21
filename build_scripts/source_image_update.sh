#!/usr/bin/env bash

mode=$1
tag=$2

if [ "$mode" = "" ] || [ "$tag" = "" ]
then
    echo "Usage: $0 <extension-branch> <image-tag>"
    exit 1
fi

./build_all.sh $mode $tag

# Define the new image URLs
NEW_AIGC_WEBUI_INFERENCE="public.ecr.aws/aws-gcr-solutions/stable-diffusion-aws-extension/aigc-webui-inference:${tag}"
NEW_AIGC_WEBUI_UTILS="public.ecr.aws/aws-gcr-solutions/stable-diffusion-aws-extension/aigc-webui-utils:${tag}"
NEW_AIGC_WEBUI_DREAMBOOTH_TRAINING="public.ecr.aws/aws-gcr-solutions/stable-diffusion-aws-extension/aigc-webui-dreambooth-training:${tag}"

# Update the Docker image URLs in dockerImages.ts
sed -i -E -e "s|(AIGC_WEBUI_INFERENCE: string = ')[^']*'|\\1$NEW_AIGC_WEBUI_INFERENCE'|g" ../infrastructure/src/common/dockerImages.ts
sed -i -E -e "s|(AIGC_WEBUI_UTILS: string = ')[^']*'|\\1$NEW_AIGC_WEBUI_UTILS'|g" ../infrastructure/src/common/dockerImages.ts
sed -i -E -e "s|(AIGC_WEBUI_DREAMBOOTH_TRAINING: string = ')[^']*'|\\1$NEW_AIGC_WEBUI_DREAMBOOTH_TRAINING'|g" ../infrastructure/src/common/dockerImages.ts
