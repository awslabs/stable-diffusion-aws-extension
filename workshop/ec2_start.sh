#!/bin/bash

export AWS_REGION=ap-northeast-1
export ESD_VERSION='dev'
export CONTAINER_NAME='comfy_ec2'

aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin 366590864501.dkr.ecr.$AWS_REGION.amazonaws.com
docker pull 366590864501.dkr.ecr.$AWS_REGION.amazonaws.com/esd-inference:$ESD_VERSION
docker build -f Dockerfile.inference.from_scratch -t ec2-start .

docker rm "$CONTAINER_NAME" || true

docker run -v ~/.aws:/root/.aws \
           -v ./:/home/ubuntu/ComfyUI \
           --gpus all \
           --name "$CONTAINER_NAME" \
           -it -p 8189:8189 ec2-start
