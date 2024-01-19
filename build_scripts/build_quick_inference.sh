#!/usr/bin/env bash

# This script shows how to build the Docker image and push it to ECR

# The argument to this script is the image name. This will be used as the image on the local
# machine and combined with the account and region to form the repository name for ECR.
# mode=$1
# tag=$2
# commit_id=$3

# if [ "$mode" = "" ] || [ "$tag" = "" ] || [ "$commit_id" = "" ]
# then
#     echo "Usage: $0 <extension-branch> <image-tag> <commit_id>"
#     exit 1
# fi

./build_and_push.sh Dockerfile.inference.quick aigc-webui-inference feature/inference-optimize inference-optimize 