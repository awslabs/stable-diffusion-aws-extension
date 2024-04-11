@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

set INITIAL_SUPPORT_COMMIT_ROOT=bef51aed032c0aaa5cfd80445bc4cf0d85b408b5
set INITIAL_SUPPORT_COMMIT_CONTROLNET=2a210f0489a4484f55088159bbfa51aaf73e10d9
set INITIAL_SUPPORT_COMMIT_TILEDVAE=f9f8073e64f4e682838f255215039ba7884553bf
set INITIAL_SUPPORT_COMMIT_REMBG=a4c07b857e73f3035f759876797fa6de986def3d
set INITIAL_SUPPORT_COMMIT_REACTOR=0185d7a2afa4a3c76b304314233a1cafd1cf4842

# Clone stable-diffusion-webui
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git

# Go to stable-diffusion-webui directory
cd stable-diffusion-webui
# Reset to specific commit
git reset --hard %INITIAL_SUPPORT_COMMIT_ROOT%

# Go to "extensions" directory
cd extensions

# Clone stable-diffusion-aws-extension
git clone https://github.com/awslabs/stable-diffusion-aws-extension.git

# Checkout aigc branch
cd stable-diffusion-aws-extension
cd ..

# Clone sd-webui-controlnet
git clone https://github.com/Mikubill/sd-webui-controlnet.git

# Go to sd-webui-controlnet directory and reset to specific commit
cd sd-webui-controlnet
git reset --hard %INITIAL_SUPPORT_COMMIT_CONTROLNET%
cd ..

# Clone stable-diffusion-webui-rembg
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui-rembg.git

# Go to stable-diffusion-webui-rembg directory and reset to specific commit
cd stable-diffusion-webui-rembg
git reset --hard %INITIAL_SUPPORT_COMMIT_REMBG%
cd ..

# Clone Tiled VAE
git clone https://github.com/pkuliyi2015/multidiffusion-upscaler-for-automatic1111.git

# Go to multidiffusion-upscaler-for-automatic1111 and reset to specific commit
cd multidiffusion-upscaler-for-automatic1111
git reset --hard %INITIAL_SUPPORT_COMMIT_TILEDVAE%
cd ..

git clone https://github.com/Gourieff/sd-webui-reactor.git --branch main --single-branch
cd sd-webui-reactor
git reset --hard %INITIAL_SUPPORT_COMMIT_REACTOR%
cd ..
