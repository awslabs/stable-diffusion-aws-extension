#!/bin/bash

# Warning: This script is used to install the initial support for client and workshop
# Warning: For keeping the same version of the initial support

set -euxo pipefail

INITIAL_SUPPORT_COMMIT_ROOT=cf2772fab0af5573da775e7437e6acdca424f26e
INITIAL_SUPPORT_COMMIT_CONTROLNET=7a4805c8ea3256a0eab3512280bd4f84ca0c8182
INITIAL_SUPPORT_COMMIT_DREAMBOOTH=c2a5617c587b812b5a408143ddfb18fc49234edf
INITIAL_SUPPORT_COMMIT_TILEDVAE=f9f8073e64f4e682838f255215039ba7884553bf
INITIAL_SUPPORT_COMMIT_REMBG=3d9eedbbf0d585207f97d5b21e42f32c0042df70

git_reduce="false"
if [ -n "$1" ]; then
    echo "reduce git enabled"
    git_reduce="true"
else
    echo "full git enabled"
fi

rm -rf "stable-diffusion-webui"

# Clone stable-diffusion-webui
REPO=https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
git clone $REPO --branch master --single-branch
# Go to stable-diffusion-webui directory
cd stable-diffusion-webui
# Reset to specific commit
git reset --hard ${INITIAL_SUPPORT_COMMIT_ROOT}
if [ "$1" = "reduce" ]; then
    rm -rf .git
    git init
    git add .gitignore
    git commit -m "Initial support"
    git branch -M main
    git remote add origin $REPO
fi

# Go to "extensions" directory
cd extensions

# Clone stable-diffusion-aws-extension
REPO=https://github.com/awslabs/stable-diffusion-aws-extension.git
git clone $REPO --branch main
# Checkout aigc branch
cd stable-diffusion-aws-extension
if [ "$1" = "reduce" ]; then
    rm -rf .git
    git init
    git add .gitignore
    git commit -m "Initial support"
    git branch -M main
    git remote add origin $REPO
fi
cd ..

# Clone sd-webui-controlnet
REPO=https://github.com/Mikubill/sd-webui-controlnet.git
git clone $REPO --branch main --single-branch
# Go to sd-webui-controlnet directory and reset to specific commit
cd sd-webui-controlnet
git reset --hard ${INITIAL_SUPPORT_COMMIT_CONTROLNET}
if [ "$1" = "reduce" ]; then
    rm -rf .git
    git init
    git add .gitignore
    git commit -m "Initial support"
    git branch -M main
    git remote add origin $REPO
fi
cd ..

# Clone stable-diffusion-webui-rembg
REPO=https://github.com/AUTOMATIC1111/stable-diffusion-webui-rembg.git
git clone $REPO --branch master --single-branch
cd stable-diffusion-webui-rembg
git reset --hard ${INITIAL_SUPPORT_COMMIT_REMBG}
if [ "$1" = "reduce" ]; then
    rm -rf .git
    git init
    git add .gitignore
    git commit -m "Initial support"
    git branch -M main
    git remote add origin $REPO
fi
cd ..

# Clone sd_dreambooth_extension
REPO=https://github.com/d8ahazard/sd_dreambooth_extension.git
git clone $REPO --branch main --single-branch
# Go to sd_dreambooth_extension directory and reset to specific commit
cd sd_dreambooth_extension
git reset --hard ${INITIAL_SUPPORT_COMMIT_DREAMBOOTH}
if [ "$1" = "reduce" ]; then
    rm -rf .git
    git init
    git add .gitignore
    git commit -m "Initial support"
    git branch -M main
    git remote add origin $REPO
fi
cd ..

# Clone Tiled VAE
REPO=https://github.com/pkuliyi2015/multidiffusion-upscaler-for-automatic1111.git
git clone $REPO --branch main --single-branch
cd multidiffusion-upscaler-for-automatic1111
git reset --hard ${INITIAL_SUPPORT_COMMIT_TILEDVAE}
if [ "$1" = "reduce" ]; then
    rm -rf .git
    git init
    git add .gitignore
    git commit -m "Initial support"
    git branch -M main
    git remote add origin $REPO
fi
cd ..
