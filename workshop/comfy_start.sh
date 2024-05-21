#!/bin/bash

download_conda(){
  echo "---------------------------------------------------------------------------------"
  mkdir -p /home/ubuntu/conda/lib/
  wget -qO /home/ubuntu/conda/lib/libcufft.so.10 https://huggingface.co/elonniu/esd/resolve/main/libcufft.so.10
  wget -qO /home/ubuntu/conda/lib/libcurand.so.10 https://huggingface.co/elonniu/esd/resolve/main/libcurand.so.10
  set_conda
}

set_conda(){
    echo "set conda environment..."
    export LD_LIBRARY_PATH=/home/ubuntu/conda/lib:$LD_LIBRARY_PATH
}

download_conda

cd /home/ubuntu || exit 1

if [ -d "/home/ubuntu/ComfyUI/venv" ]; then
    cd /home/ubuntu/ComfyUI || exit 1
    rm -rf web/extensions/ComfyLiterals
    chmod -R +x venv
    source venv/bin/activate
    python3 main.py --listen 0.0.0.0 --port 8189 --cuda-malloc
    exit 1
fi

curl -sSL "https://raw.githubusercontent.com/awslabs/stable-diffusion-aws-extension/dev/build_scripts/install_comfy.sh" | bash;
rm ./ComfyUI/custom_nodes/comfy_sagemaker_proxy.py

cd /home/ubuntu/ComfyUI || exit 1

mkdir -p models/vae/
wget -O models/vae/vae-ft-mse-840000-ema-pruned.safetensors https://huggingface.co/stabilityai/sd-vae-ft-mse-original/resolve/main/vae-ft-mse-840000-ema-pruned.safetensors

#mkdir -p models/checkpoints/
#wget -O models/checkpoints/majicmixRealistic_v7.safetensors https://huggingface.co/GreenGrape/231209/resolve/045ebfc504c47ba8ccc424f1869c65a223d1f5cc/majicmixRealistic_v7.safetensors
#
#mkdir -p models/animatediff_models/
#wget -O models/animatediff_models/mm_sd_v15_v2.ckpt https://huggingface.co/guoyww/animatediff/resolve/main/mm_sd_v15_v2.ckpt

chmod -R 777 /home/ubuntu/ComfyUI

chmod -R +x venv
source venv/bin/activate
pip install dynamicprompts

rm -rf web/extensions/ComfyLiterals

python3 main.py --listen 0.0.0.0 --port 8189 --cuda-malloc
exit 1