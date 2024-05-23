#!/bin/bash

set -euxo pipefail

if [ -f "/etc/environment" ]; then
    source /etc/environment
fi

SERVICE_TYPE="comfy"

export CONTAINER_NAME="esd_container"
export ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
export AWS_REGION=$(aws configure get region)

image="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$CONTAINER_NAME:latest"

docker stop "$CONTAINER_NAME" || true
docker rm "$CONTAINER_NAME" || true

# Check if the repository already exists
if aws ecr describe-repositories --region "$AWS_REGION" --repository-names "$CONTAINER_NAME" >/dev/null 2>&1; then
    echo "ECR repository '$CONTAINER_NAME' already exists."
else
    echo "ECR repository '$CONTAINER_NAME' does not exist. Creating..."
    aws ecr create-repository --repository-name --region "$AWS_REGION" "$CONTAINER_NAME" | jq .
    echo "ECR repository '$CONTAINER_NAME' created successfully."
fi

aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "366590864501.dkr.ecr.$AWS_REGION.amazonaws.com"
docker pull "366590864501.dkr.ecr.$AWS_REGION.amazonaws.com/esd-inference:$ESD_VERSION"
docker build -f Dockerfile \
             --build-arg AWS_REGION="$AWS_REGION" \
             --build-arg ESD_VERSION="$ESD_VERSION" \
             -t "$image" .

image_hash=$(docker inspect "$image"  | jq -r ".[0].Id")
image_hash=${image_hash:7}

release_image="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$CONTAINER_NAME:$image_hash"
docker tag "$image" "$release_image"

aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
echo "docker push $release_image"
docker push "$release_image"
echo "docker pushed $release_image"

echo "Starting container..."
# local vol can be replace with your local directory
local_volume="./container/$SERVICE_TYPE"
mkdir -p $local_volume

if [ -n "${WORKFLOW_NAME-}" ]; then
    echo "WORKFLOW_NAME is $WORKFLOW_NAME"
else
   export WORKFLOW_NAME=""
fi

total_memory=$(cat /proc/meminfo | grep 'MemTotal' | awk '{print $2}')
total_memory_mb=$((total_memory / 1024))
echo "total_memory_mb: $total_memory_mb"
limit_memory_mb=$((total_memory_mb - 2048))
echo "limit_memory_mb: $limit_memory_mb"

#  -v ./build_scripts/comfy/comfy_proxy.py:/home/ubuntu/ComfyUI/custom_nodes/comfy_proxy.py \
docker run -v ~/.aws:/root/.aws \
           -v "$local_volume":/home/ubuntu \
           -v ./build_scripts/inference/start.sh:/start.sh \
           -v ./build_scripts/comfy/comfy_proxy.py:/home/ubuntu/ComfyUI/custom_nodes/comfy_proxy.py \
           --gpus all \
           -e "IMAGE_HASH=$release_image" \
           -e "ESD_VERSION=$ESD_VERSION" \
           -e "SERVICE_TYPE=$SERVICE_TYPE" \
           -e "ON_EC2=true" \
           -e "S3_BUCKET_NAME=$COMFY_BUCKET_NAME" \
           -e "AWS_REGION=$AWS_REGION" \
           -e "AWS_DEFAULT_REGION=$AWS_REGION" \
           -e "COMFY_API_URL=$COMFY_API_URL" \
           -e "COMFY_API_TOKEN=$COMFY_API_TOKEN" \
           -e "COMFY_ENDPOINT=$COMFY_ENDPOINT" \
           -e "COMFY_BUCKET_NAME=$COMFY_BUCKET_NAME" \
           -e "PROCESS_NUMBER=$PROCESS_NUMBER" \
           -e "WORKFLOW_NAME=$WORKFLOW_NAME" \
           --name "$CONTAINER_NAME" \
           -p 8188-8288:8188-8288 \
           --memory "${limit_memory_mb}mb" \
           "$image"