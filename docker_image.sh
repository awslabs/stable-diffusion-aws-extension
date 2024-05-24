#!/bin/bash

#set -euxo pipefail

export ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
export AWS_REGION=$(aws configure get region)
repository_url="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/esd_container"
current_image=""

while true; do
    if [ -f "./container/image" ]; then
        image_name=$(cat "./container/image")

        if [ "$image_name" = "$current_image" ]; then
            sleep 10
            continue
        fi

        current_image=$image_name

        release_image="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/esd_container:$image_name"
        aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
        docker tag "comfy_8188:latest" "$release_image"
        docker push "$release_image"
        untagged_images=$(docker images --filter "dangling=true" -q)
        for image_id in $untagged_images; do
            docker rmi -f "$image_id"
        done
    fi
    sleep 10
done

exit 1
