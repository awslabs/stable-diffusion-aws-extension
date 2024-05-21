#!/bin/bash

set -euxo pipefail

s5cmd ls

aws s3 ls

aws sts get-caller-identity

printenv

download_conda(){
  echo "---------------------------------------------------------------------------------"
  mkdir -p /home/ubuntu/conda/lib/
  wget -qO /home/ubuntu/conda/lib/libcufft.so.10 https://huggingface.co/elonniu/esd/resolve/main/libcufft.so.10
  wget -qO /home/ubuntu/conda/lib/libcurand.so.10 https://huggingface.co/elonniu/esd/resolve/main/libcurand.so.10
  set_conda
}

set_conda(){
    echo "set conda environment..."
    export LD_LIBRARY_PATH=/home/ubuntu/conda/lib:$LD_PRELOAD
}

download_conda

cd /home/ubuntu || exit 1

if [ -d "/home/ubuntu/ComfyUI/venv" ]; then
    cd /home/ubuntu/ComfyUI || exit 1
    rm -rf web/extensions/ComfyLiterals
    chmod -R +x venv
    source venv/bin/activate
    python3 main.py --listen 0.0.0.0 --port 8188 --cuda-malloc
    exit 1
fi

#export CACHE_PUBLIC_COMFY="aws-gcr-solutions-$AWS_REGION/stable-diffusion-aws-extension-github-mainline/$ESD_VERSION/comfy.tar"
#echo "downloading comfy file $CACHE_PUBLIC_COMFY ..."
#
#start_at=$(date +%s)
#s5cmd cp "s3://$CACHE_PUBLIC_COMFY" /home/ubuntu/
#end_at=$(date +%s)
#export DOWNLOAD_FILE_SECONDS=$((end_at-start_at))
#echo "download file: $DOWNLOAD_FILE_SECONDS seconds"
#
#echo "decompressing comfy file..."
#start_at=$(date +%s)
#tar --overwrite -xf "$SERVICE_TYPE.tar" -C /home/ubuntu/
#rm -rf "comfy.tar"
#end_at=$(date +%s)
#export DECOMPRESS_SECONDS=$((end_at-start_at))
#echo "decompress file: $DECOMPRESS_SECONDS seconds"

curl -sSL "https://raw.githubusercontent.com/awslabs/stable-diffusion-aws-extension/dev/build_scripts/install_comfy.sh" | bash;
rm ./ComfyUI/custom_nodes/comfy_sagemaker_proxy.py

cd /home/ubuntu/ComfyUI || exit 1

mkdir -p models/vae/
wget -O --quiet models/vae/vae-ft-mse-840000-ema-pruned.safetensors "https://huggingface.co/stabilityai/sd-vae-ft-mse-original/resolve/main/vae-ft-mse-840000-ema-pruned.safetensors"

#mkdir -p models/checkpoints/
#wget -O --quiet models/checkpoints/majicmixRealistic_v7.safetensors "https://huggingface.co/GreenGrape/231209/resolve/045ebfc504c47ba8ccc424f1869c65a223d1f5cc/majicmixRealistic_v7.safetensors"

mkdir -p models/animatediff_models/
wget -O --quiet models/animatediff_models/mm_sd_v15_v2.ckpt "https://huggingface.co/guoyww/animatediff/resolve/main/mm_sd_v15_v2.ckpt"

wget -O --quiet models/checkpoints/v1-5-pruned-emaonly.ckpt "https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.ckpt?download=true"

chmod -R 777 /home/ubuntu/ComfyUI

chmod -R +x venv
source venv/bin/activate

pip install dynamicprompts
pip install ultralytics

rm -rf web/extensions/ComfyLiterals

start_comfy(){
  port=$1
  python3 main.py --listen 0.0.0.0 --port "$port" --cuda-malloc
}

init_port=8188
for i in $(seq 1 "$PROCESS_NUMBER"); do
    if [ "$i" -eq "$PROCESS_NUMBER" ]; then
        start_comfy $init_port
        break
    fi
    start_comfy $init_port &
    init_port=$((init_port + i))
done

exit 1
