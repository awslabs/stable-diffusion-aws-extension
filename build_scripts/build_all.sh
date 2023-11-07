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

./build_and_push.sh Dockerfile.aigc-endpoint-byoc.from_scratch aigc-endpoint-byoc $branch $tag $commit_id

./build_and_push.sh Dockerfile.aigc-endpoint-diffusers.from_scratch aigc-endpoint-diffusers $branch $tag $commit_id

./build_and_push.sh Dockerfile.aigc-job.from_scratch aigc-job $branch $tag $commit_id

./build_and_push_byoc.sh Dockerfile.aigc-endpoint-byoc.from_scratch aigc-endpoint-byoc $branch $tag $commit_id

./build_and_push_byoc.sh Dockerfile.aigc-endpoint-diffusers.from_scratch aigc-endpoint-diffusers $branch $tag $commit_id

./build_and_push_byoc.sh Dockerfile.aigc-job.from_scratch aigc-job $branch $tag $commit_id