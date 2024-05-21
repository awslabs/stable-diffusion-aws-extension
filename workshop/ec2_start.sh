#!/bin/bash

export ESD_VERSION='dev'
export CONTAINER_NAME='comfy_ec2'

aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin 366590864501.dkr.ecr."$AWS_REGION".amazonaws.com
docker pull 366590864501.dkr.ecr."$AWS_REGION".amazonaws.com/esd-inference:$ESD_VERSION
docker build -f Dockerfile.comfy \
             --build-arg ESD_VERSION='ec2' \
             --build-arg S3_BUCKET_NAME='elonniu' \
             --build-arg SERVICE_TYPE='comfy' \
             --build-arg AWS_REGION="$AWS_REGION" \
             --build-arg ON_EC2='true' \
             --build-arg COMFY_API_URL="$COMFY_API_URL" \
             --build-arg COMFY_API_TOKEN="$COMFY_API_TOKEN" \
             --build-arg COMFY_ENDPOINT="$COMFY_ENDPOINT" \
             --build-arg COMFY_NEED_SYNC="$COMFY_NEED_SYNC" \
             --build-arg COMFY_BUCKET_NAME="$COMFY_BUCKET_NAME" \
             -t ec2-start .

docker rm "$CONTAINER_NAME" || true

mkdir -p ComfyUI

docker run -v ~/.aws:/root/.aws \
           -v ./ComfyUI:/home/ubuntu/ComfyUI \
           --gpus all \
           --name "$CONTAINER_NAME" \
           -it -p 8189:8189 ec2-start
