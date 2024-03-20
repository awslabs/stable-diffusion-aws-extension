#!/bin/bash

trap 'echo "error_lock" > /error_lock; exit 1' ERR
if [ -f "/error_lock" ]; then
    echo "start failed, please check the log"
    sleep 30
    exit 1
fi

echo "Current shell: $SHELL"
echo "Running in $(bash --version)"

nvidia-smi

ESD_FILE_VERSION='1.5.0'

echo "---------------------------------------------------------------------------------"
echo "INSTANCE_TYPE: $INSTANCE_TYPE"
echo "INSTANCE_PACKAGE: $INSTANCE_PACKAGE"
echo "ENDPOINT_NAME: $ENDPOINT_NAME"
echo "ENDPOINT_ID: $ENDPOINT_ID"
echo "ESD_FILE_VERSION: $ESD_FILE_VERSION"
echo "CREATED_AT: $CREATED_AT"
created_time_seconds=$(date -d "$CREATED_AT" +%s)
current_time=$(date "+%Y-%m-%dT%H:%M:%S.%6N")
current_time_seconds=$(date -d "$current_time" +%s)
init_seconds=$(( current_time_seconds - created_time_seconds ))
echo "NOW_AT: $current_time"
echo "Init from Create: $init_seconds seconds"

echo "---------------------------------------------------------------------------------"
export AWS_REGION="us-west-2"
s5cmd --log=error cp "s3://aws-gcr-solutions-us-west-2/extension-for-stable-diffusion-on-aws/1.5.0-g5/conda/libcufft.so.10" /opt/conda/lib/
s5cmd --log=error cp "s3://aws-gcr-solutions-us-west-2/extension-for-stable-diffusion-on-aws/1.5.0-g5/conda/libcurand.so.10" /opt/conda/lib/
export LD_LIBRARY_PATH=/opt/conda/lib:$LD_LIBRARY_PATH
export AWS_REGION=$AWS_DEFAULT_REGION
echo "---------------------------------------------------------------------------------"

check_ready() {
  while true; do
    PID=$(lsof -i :8080 | awk 'NR!=1 {print $2}' | head -1)

    if [ -n "$PID" ]; then
      tar_file="esd-$ESD_FILE_VERSION-$INSTANCE_PACKAGE.tar"
      echo "Port 8080 is in use by PID: $PID. tar files and upload to S3"
      echo "tar -cvf $tar_file /home/ubuntu/stable-diffusion-webui/"
      tar -cvf $tar_file /home/ubuntu/stable-diffusion-webui/ > /dev/null 2>&1
      s5cmd sync $tar_file "s3://$BUCKET_NAME/"
      break
    else
      echo "Port 8080 is not in use, waiting for 10 seconds..."
    fi

    sleep 10
  done
}

check_ready &

export INSTALL_SCRIPT=https://raw.githubusercontent.com/awslabs/stable-diffusion-aws-extension/dev/install.sh

cd /home/ubuntu
curl -sSL "$INSTALL_SCRIPT" | bash;

cd stable-diffusion-webui
python3 -m venv venv;

chmod +x /home/ubuntu/stable-diffusion-webui/venv/bin/*

source venv/bin/activate

mkdir tools
cp /usr/local/bin/s5cmd ./tools/

python -m pip install --upgrade pip
python -m pip install accelerate
python -m pip install markdown

python -m pip install onnxruntime-gpu
python -m pip install insightface==0.7.3

export TORCH_INDEX_URL="https://download.pytorch.org/whl/cu118"
export TORCH_COMMAND="pip install torch==2.0.1 torchvision==0.15.2 --extra-index-url $TORCH_INDEX_URL"
export XFORMERS_PACKAGE="xformers==0.0.20"

# if $EXTENSIONS is not empty, it will be executed
if [ -n "$EXTENSIONS" ]; then
    echo "---------------------------------------------------------------------------------"
    cd /home/ubuntu/stable-diffusion-webui/extensions/ || exit 1

    read -ra array <<< "$(echo "$EXTENSIONS" | tr "," " ")"

    for git_repo in "${array[@]}"; do
      start_at=$(date +%s)
      echo "git clone $git_repo"
      git clone "$git_repo"
      end_at=$(date +%s)
      cost=$((end_at-start_at))
      echo "git clone $git_repo: $cost seconds"
    done
fi

cd /home/ubuntu/stable-diffusion-webui
accelerate launch --num_cpu_threads_per_process=6 launch.py --api --listen --port 8080 --xformers --no-half-vae --no-download-sd-model --no-hashing --nowebui --skip-torch-cuda-test
