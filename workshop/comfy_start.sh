#!/bin/bash

set -euxo pipefail

echo "---------------------------------------------------------------------------------"
printenv
echo "---------------------------------------------------------------------------------"

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

start_process(){
  echo "---------------------------------------------------------------------------------"
  init_port=8187
  for i in $(seq 1 "$PROCESS_NUMBER"); do
      init_port=$((init_port + 1))

      if [ "$i" -eq "$PROCESS_NUMBER" ]; then
          python3 main.py --listen 0.0.0.0 \
                          --port "$init_port" \
                          --cuda-malloc \
                          --output-directory "/home/ubuntu/ComfyUI/output/$init_port" \
                          --temp-directory "/home/ubuntu/ComfyUI/temp/$init_port"
          exit 1
      fi

      nohup python3 main.py --listen 0.0.0.0 \
                            --port "$init_port" \
                            --cuda-malloc \
                            --output-directory "/home/ubuntu/ComfyUI/output/$init_port" \
                            --temp-directory "/home/ubuntu/ComfyUI/temp/$init_port" &
  done
}

download_conda

cd /home/ubuntu || exit 1

if [ -d "/home/ubuntu/ComfyUI/venv" ]; then
    cd /home/ubuntu/ComfyUI || exit 1
    rm -rf web/extensions/ComfyLiterals
    chmod -R +x venv
    source venv/bin/activate
    start_process
    exit 1
fi

export CACHE_PUBLIC_COMFY="aws-gcr-solutions-$AWS_REGION/stable-diffusion-aws-extension-github-mainline/$ESD_VERSION/comfy.tar"
echo "downloading comfy file $CACHE_PUBLIC_COMFY ..."

start_at=$(date +%s)
s5cmd cp "s3://$CACHE_PUBLIC_COMFY" /home/ubuntu/
end_at=$(date +%s)
export DOWNLOAD_FILE_SECONDS=$((end_at-start_at))
echo "download file: $DOWNLOAD_FILE_SECONDS seconds"

echo "decompressing comfy file..."
start_at=$(date +%s)
tar --overwrite -xf "$SERVICE_TYPE.tar" -C /home/ubuntu/
rm -rf "comfy.tar"
end_at=$(date +%s)
export DECOMPRESS_SECONDS=$((end_at-start_at))
echo "decompress file: $DECOMPRESS_SECONDS seconds"

ls -la

rm ./ComfyUI/custom_nodes/comfy_sagemaker_proxy.py

cd /home/ubuntu/ComfyUI || exit 1
rm -rf web/extensions/ComfyLiterals
chmod -R +x venv
source venv/bin/activate

pip install dynamicprompts
pip install ultralytics

mkdir -p models/vae/
wget --quiet -O models/vae/vae-ft-mse-840000-ema-pruned.safetensors "https://huggingface.co/stabilityai/sd-vae-ft-mse-original/resolve/main/vae-ft-mse-840000-ema-pruned.safetensors"

mkdir -p models/checkpoints/
wget --quiet -O models/checkpoints/majicmixRealistic_v7.safetensors "https://huggingface.co/GreenGrape/231209/resolve/045ebfc504c47ba8ccc424f1869c65a223d1f5cc/majicmixRealistic_v7.safetensors"

mkdir -p models/animatediff_models/
wget --quiet -O models/animatediff_models/mm_sd_v15_v2.ckpt "https://huggingface.co/guoyww/animatediff/resolve/main/mm_sd_v15_v2.ckpt"

wget --quiet -O models/checkpoints/v1-5-pruned-emaonly.ckpt "https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.ckpt?download=true"

chmod -R 777 /home/ubuntu/ComfyUI

start_process

exit 1
