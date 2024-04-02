#!/bin/bash

echo "---------------------------------------------------------------------------------"
echo "install comfy..."

branch=main

if [[ $ESD_CODE_BRANCH == "dev" ]]; then
  branch=dev
fi

export INITIAL_COMFY_COMMIT_ROOT=e6482fbbfc83cd25add0532b2e4c51d305e8a232

rm -rf ComfyUI
rm -rf stable-diffusion-aws-extension

git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI || exit 1
git reset --hard ${INITIAL_COMFY_COMMIT_ROOT}
cd ../

git clone https://github.com/awslabs/stable-diffusion-aws-extension.git --branch "$branch" --single-branch

cp stable-diffusion-aws-extension/build_scripts/comfy/serve.py ComfyUI/
cp stable-diffusion-aws-extension/build_scripts/comfy/comfy_sagemaker_proxy.py ComfyUI/custom_nodes/

echo "---------------------------------------------------------------------------------"
echo "build comfy..."

cd ComfyUI || exit 1

if [ "$ON_DOCKER" == "true" ]; then
  python3 -m venv venv

  source venv/bin/activate

  pip install --upgrade pip
  pip install -r requirements.txt
  pip install boto3
  pip install aws_xray_sdk
  pip install fastapi
  pip install uvicorn
  pip install torch==2.0.1 torchvision==0.15.2 --extra-index-url https://download.pytorch.org/whl/cu118
  pip install https://github.com/openai/CLIP/archive/d50d76daa670286dd6cacf3bcd80b5e4823fc8e1.zip
  pip install https://github.com/mlfoundations/open_clip/archive/bb6e834e9c70d9c27d0dc3ecedeebeaeb1ffad6b.zip
  pip install open-clip-torch==2.20.0
else
  pip install --upgrade pip
  pip install -r requirements.txt
  pip install boto3
  pip install aws_xray_sdk
  pip install fastapi
  pip install uvicorn
fi
