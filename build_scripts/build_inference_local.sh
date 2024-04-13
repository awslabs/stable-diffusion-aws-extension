#!/usr/bin/env bash

export AWS_PROFILE=default

./build_and_push_local.sh Dockerfile.inference.from_scratch esd-inference dev "dev"
