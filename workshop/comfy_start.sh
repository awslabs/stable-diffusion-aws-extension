#!/bin/bash

if [ -n "$ON_EC2" ]; then
    cd /home/ubuntu || exit 1

    if [ -d "venv" ]; then
        cd /home/ubuntu/ComfyUI || exit 1
        rm -rf web/extensions/ComfyLiterals
        chmod -R +x venv
        source venv/bin/activate
        python3 main.py --listen 0.0.0.0 --port 8189 --cuda-malloc
        exit 1
    fi

    sudo curl -sSL "https://raw.githubusercontent.com/awslabs/stable-diffusion-aws-extension/dev/build_scripts/install_comfy.sh" | sudo bash;
    sudo rm ./ComfyUI/custom_nodes/comfy_sagemaker_proxy.py


    cd /home/ubuntu/ComfyUI || exit 1

    chmod -R +x venv
    source venv/bin/activate
    pip install dynamicprompts

    rm -rf web/extensions/ComfyLiterals

    python3 main.py --listen 0.0.0.0 --port 8189 --cuda-malloc
    exit 1
fi

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
cd "$APP_CWD" || exit 1
chown -R root:root venv
chmod -R +x venv
source venv/bin/activate

python3 /metrics.py &
python3 /serve.py

#python main.py --listen 0.0.0.0 --port 23000 --output-directory /home/ubuntu/ComfyUI/output/0/ --temp-directory /home/ubuntu/ComfyUI/temp/0/ --cuda-device 0 --cuda-malloc

exit 1
