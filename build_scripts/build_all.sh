#!/usr/bin/env bash

# This script shows how to build the Docker image and push it to ECR to be ready for use
# by Braket.

# The argument to this script is the image name. This will be used as the image on the local
# machine and combined with the account and region to form the repository name for ECR.
mode=$1
tag=$2

if [ "$mode" = "" ] || [ "$tag" = "" ]
then
    echo "Usage: $0 <extension-branch> <image-tag>"
    exit 1
fi

./build_and_push.sh Dockerfile.inference.from_scratch aigc-webui-inference $mode $tag

./build_and_push.sh Dockerfile.utils.from_scratch aigc-webui-utils $mode $tag

./build_and_push.sh Dockerfile.dreambooth.from_scratch aigc-webui-dreambooth-training $mode $tag