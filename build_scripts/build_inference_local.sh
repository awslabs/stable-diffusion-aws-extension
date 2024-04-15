#!/usr/bin/env bash

export AWS_PROFILE=default

./build_and_push_local.sh Dockerfile.inference.from_scratch esd-inference dev "dev"

export AWS_PROFILE=gcr
export AWS_DEFAULT_REGION=cn-north-1
./build_and_push_local.sh Dockerfile.inference.cn.sd.from_scratch esd-inference dev "sd-cn"
