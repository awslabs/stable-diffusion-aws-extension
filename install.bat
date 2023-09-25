@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

set INITIAL_SUPPORT_COMMIT_ROOT=5ef669de080814067961f28357256e8fe27544f4
set INITIAL_SUPPORT_COMMIT_CONTROLNET=e67e017731aad05796b9615dc6eadce911298ea1
set INITIAL_SUPPORT_COMMIT_DREAMBOOTH=c2a5617c587b812b5a408143ddfb18fc49234edf
set INITIAL_SUPPORT_COMMIT_REMBG=3d9eedbbf0d585207f97d5b21e42f32c0042df70
set INITIAL_SUPPORT_COMMIT_SAM=c555c6d9c4e1d14b018e4d2a92acd47765536585
set INITIAL_SUPPORT_COMMIT_TILEDVAE=f9f8073e64f4e682838f255215039ba7884553bf


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

# Clone sd_dreambooth_extension
git clone https://github.com/d8ahazard/sd_dreambooth_extension.git

# Go to sd_dreambooth_extension directory and reset to specific commit
cd sd_dreambooth_extension
git reset --hard %INITIAL_SUPPORT_COMMIT_DREAMBOOTH%
cd ..

# Clone stable-diffusion-webui-rembg
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui-rembg.git

# Go to stable-diffusion-webui-rembg directory and reset to specific commit
cd stable-diffusion-webui-rembg
git reset --hard %INITIAL_SUPPORT_COMMIT_REMBG%
cd ..

# Clone sd-webui-segment-anything
git clone https://github.com/continue-revolution/sd-webui-segment-anything.git

# Go to sd-webui-segment-anything directory and reset to specific commit
cd sd-webui-segment-anything
git reset --hard %INITIAL_SUPPORT_COMMIT_SAM%
cd ..


# Clone Tiled VAE
git clone https://github.com/pkuliyi2015/multidiffusion-upscaler-for-automatic1111.git

# Go to multidiffusion-upscaler-for-automatic1111 and reset to specific commit
cd multidiffusion-upscaler-for-automatic1111
git reset --hard ${INITIAL_SUPPORT_COMMIT_TILEDVAE}
cd ..