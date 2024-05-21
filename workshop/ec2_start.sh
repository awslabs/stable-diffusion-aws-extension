#!/bin/bash

#set -euxo pipefail

export ESD_VERSION='dev'
export CONTAINER_NAME='comfy_ec2'
export ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
export AWS_REGION=$(aws configure get region)

repository_name="comfy-ec2"
image="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$repository_name:latest"

docker stop "$CONTAINER_NAME" || true
docker rm "$CONTAINER_NAME" || true

# Check if the repository already exists
if aws ecr describe-repositories --region "$AWS_REGION" --repository-names "$repository_name" >/dev/null 2>&1; then
    echo "ECR repository '$repository_name' already exists."
else
    echo "ECR repository '$repository_name' does not exist. Creating..."
    aws ecr create-repository --repository-name --region "$AWS_REGION" "$repository_name"
    echo "ECR repository '$repository_name' created successfully."
fi

aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin 366590864501.dkr.ecr."$AWS_REGION".amazonaws.com
docker pull 366590864501.dkr.ecr."$AWS_REGION".amazonaws.com/esd-inference:$ESD_VERSION
docker build -f Dockerfile.comfy \
             --build-arg ESD_VERSION='ec2' \
             --build-arg SERVICE_TYPE='comfy' \
             --build-arg ON_EC2='true' \
             --build-arg S3_BUCKET_NAME="$COMFY_BUCKET_NAME" \
             --build-arg AWS_REGION="$AWS_REGION" \
             --build-arg COMFY_API_URL="$COMFY_API_URL" \
             --build-arg COMFY_API_TOKEN="$COMFY_API_TOKEN" \
             --build-arg COMFY_ENDPOINT="$COMFY_ENDPOINT" \
             --build-arg COMFY_BUCKET_NAME="$COMFY_BUCKET_NAME" \
             -t "$image" .

image_hash=$(docker inspect "$image"  | jq -r ".[0].Id")
image_hash=${image_hash:7}

release_image="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$repository_name:$image_hash"
docker tag "$image" "$release_image"
docker push "$release_image"

mkdir -p ~/ComfyUI

docker run -v ~/.aws:/root/.aws \
           -v ~/ComfyUI:/home/ubuntu/ComfyUI \
           --gpus all \
           -e "IMAGE_HASH=$release_image" \
           --name "$CONTAINER_NAME" \
           -it -p 8189:8189 "$image"
