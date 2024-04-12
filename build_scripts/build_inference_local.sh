#!/usr/bin/env bash

export AWS_PROFILE=default

if [ -z "$1" ]; then
    echo "Please provide a tag for the image"
    exit 1
fi

tag=$1
./build_and_push_local.sh Dockerfile.inference.from_scratch esd-inference dev "$tag"
