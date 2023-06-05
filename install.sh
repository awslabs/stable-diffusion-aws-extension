#!/bin/bash
  
# Clone stable-diffusion-webui
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git

# Go to stable-diffusion-webui directory
cd stable-diffusion-webui
# Reset to specific commit
git reset --hard b6af0a3809ea869fb180633f9affcae4b199ffcf

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
git reset --hard f36493878b299c367bc51f2935fd7e6d19188569
cd ..

# Clone sd_dreambooth_extension
git clone https://github.com/d8ahazard/sd_dreambooth_extension.git

# Go to sd_dreambooth_extension directory and reset to specific commit
cd sd_dreambooth_extension
git reset --hard b396af26b7906aa82a29d8847e756396cb2c28fb
cd ..