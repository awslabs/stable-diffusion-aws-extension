#!/usr/bin/env bash
#FROM 763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:2.0.1-gpu-py310-cu118-ubuntu20.04-sagemaker

git clone https://github.com/facebookresearch/xformers.git

cd xformers

git checkout v0.0.20

git submodule update --init --recursive

pip install -r requirements.txt

python setup.py build

python setup.py bdist_wheel