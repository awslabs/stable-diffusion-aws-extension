#!/usr/bin/env bash

export AWS_PROFILE=default

if [ -z "$1" ]; then
    echo "Please provide a tag for the image"
    exit 1
fi

tag=$1
./build_and_push_local.sh Dockerfile.inference.from_scratch esd-inference dev "$tag"


export AWS_PROFILE=gcr
export AWS_DEFAULT_REGION=cn-north-1
./build_and_push_local.sh Dockerfile.inference.cn.sd.from_scratch esd-inference dev "sd-cn"

export AWS_DEFAULT_REGION=cn-northwest-1
./build_and_push_local.sh Dockerfile.inference.cn.sd.from_scratch esd-inference dev "sd-cn"

export AWS_DEFAULT_REGION=cn-north-1
./build_and_push_local.sh Dockerfile.inference.cn.comfy.from_scratch esd-inference dev "comfy-cn"

export AWS_DEFAULT_REGION=cn-northwest-1
./build_and_push_local.sh Dockerfile.inference.cn.comfy.from_scratch esd-inference dev "comfy-cn"
