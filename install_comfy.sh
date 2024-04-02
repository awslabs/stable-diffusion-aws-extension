#!/bin/bash

echo "---------------------------------------------------------------------------------"
echo "install comfy..."

branch=main

# if ESD_CODE_BRANCH is dev, then use dev branch
if [[ $ESD_CODE_BRANCH == "dev" ]]; then
  branch=dev
fi

export INITIAL_COMFY_COMMIT_ROOT=bef51aed032c0aaa5cfd80445bc4cf0d85b408b5

rm -rf ComfyUI
rm -rf stable-diffusion-aws-extension

git clone https://github.com/comfyanonymous/ComfyUI.git
git clone https://github.com/awslabs/stable-diffusion-aws-extension.git --branch "$branch" --single-branch

cp stable-diffusion-aws-extension/build_scripts/comfy/serve.py ComfyUI/
cp stable-diffusion-aws-extension/build_scripts/comfy/comfy_sagemaker_proxy.py ComfyUI/custom_nodes/

echo "---------------------------------------------------------------------------------"
echo "creating venv and install packages..."

cd ComfyUI || exit 1

python3 -m venv venv

source venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install boto3
python -m pip install aws_xray_sdk
python -m pip install fastapi
python -m pip install uvicorn
python -m pip install torch==2.0.1 torchvision==0.15.2 --extra-index-url https://download.pytorch.org/whl/cu118
python -m pip install https://github.com/openai/CLIP/archive/d50d76daa670286dd6cacf3bcd80b5e4823fc8e1.zip
python -m pip install https://github.com/mlfoundations/open_clip/archive/bb6e834e9c70d9c27d0dc3ecedeebeaeb1ffad6b.zip
python -m pip install open-clip-torch==2.20.0
