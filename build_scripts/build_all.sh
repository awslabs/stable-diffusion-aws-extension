#!/usr/bin/env bash

# This script shows how to build the Docker image and push it to ECR

# The argument to this script is the image name. This will be used as the image on the local
# machine and combined with the account and region to form the repository name for ECR.
branch=$1
tag=$2
commit_id=$3

if [ "$branch" = "" ] || [ "$tag" = "" ] || [ "$commit_id" = "" ]
then
    echo "Usage: $0 <extension-branch> <image-tag> <commit_id>"
    exit 1
fi

./build_and_push.sh Dockerfile.inference.from_scratch aigc-webui-inference $branch $tag $commit_id

./build_and_push.sh Dockerfile.utils.from_scratch aigc-webui-utils $branch $tag $commit_id

./build_and_push.sh Dockerfile.dreambooth.from_scratch aigc-webui-dreambooth-training $branch $tag $commit_id
