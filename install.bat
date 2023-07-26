@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

set INITIAL_SUPPORT_COMMIT_ROOT=a3ddf464a2ed24c999f67ddfef7969f8291567be
set INITIAL_SUPPORT_COMMIT_CONTROLNET=e9679f8fc50880a92d6f1b6fc1aabad41079efd5
set INITIAL_SUPPORT_COMMIT_DREAMBOOTH=c2a5617c587b812b5a408143ddfb18fc49234edf
set INITIAL_SUPPORT_COMMIT_REMBG=3d9eedbbf0d585207f97d5b21e42f32c0042df70
set INITIAL_SUPPORT_COMMIT_SAM=ffe263155d7f3ac4ee23a96262ecb77b9899ed95

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