#!/usr/bin/env bash

tag="latest"
./build_and_push_local.sh Dockerfile.inference.from_scratch esd-inference dev $tag
