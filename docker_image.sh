#!/bin/bash

current_image=""

while true; do
    image_target_name=$(cat "$(pwd)/container/image_target_name")
    base_image_name=$(cat "$(pwd)/container/image_base")

    if [ -z "$image_target_name" ]; then
        sleep 30
        exit 1
    fi

    if [ -z "$base_image_name" ]; then
        sleep 30
        exit 1
    fi

    if [ "$current_image" = "$image_target_name" ]; then
        echo "$current_image already pushed"
        sleep 10
        continue
    fi
    current_image=$image_target_name

    export ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
    export AWS_REGION=$(aws configure get region)
    release_image="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/esd_container:$image_target_name"

    aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
    docker tag "$base_image_name" "$release_image"
    docker push "$release_image"

    untagged_images=$(docker images --filter "dangling=true" -q)
    for image_id in $untagged_images; do
        docker rmi -f "$image_id"
    done

    sleep 5
done

exit 1
