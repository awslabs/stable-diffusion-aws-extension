#!/bin/bash

#set -euxo pipefail

# -------------------- common init --------------------

if [ -z "$ESD_VERSION" ]; then
  echo "ESD_VERSION is not set"
  exit 1
fi

if [ -z "$S3_BUCKET_NAME" ]; then
  echo "S3_BUCKET_NAME is not set"
  exit 1
fi

if [ -z "$SERVICE_TYPE" ]; then
  echo "SERVICE_TYPE is not set"
  exit 1
fi

export TAR_FILE="esd.tar"
export CACHE_ENDPOINT="endpoint-$ESD_VERSION-$ENDPOINT_NAME"
export CACHE_PUBLIC="aws-gcr-solutions-$AWS_REGION/stable-diffusion-aws-extension-github-mainline/$ESD_VERSION/$SERVICE_TYPE.tar"

random_string=$(LC_ALL=C cat /dev/urandom | LC_ALL=C tr -dc 'a-z0-9' | fold -w 6 | head -n 1)
export ENDPOINT_INSTANCE_ID="$ENDPOINT_NAME-$random_string"

if [[ $IMAGE_URL == *"dev"* ]]; then
  # Enable dev mode
  trap 'echo "error_lock" > /error_lock; exit 1' ERR
  if [ -f "/error_lock" ]; then
      echo "start failed, please check the log"
      sleep 30
      exit 1
  fi
fi

cores=$(lscpu | grep "^Core(s) per socket:" | awk '{print $4}')
sockets=$(lscpu | grep "^Socket(s):" | awk '{print $2}')
export CUP_CORE_NUMS=$((cores * sockets))

echo "---------------------------------------------------------------------------------"
echo "whoami: $(whoami)"
echo "Current shell: $SHELL"
echo "Running in $(bash --version)"
echo "---------------------------------------------------------------------------------"
echo "CREATED_AT: $CREATED_AT"
created_time_seconds=$(date -d "$CREATED_AT" +%s)
current_time=$(date "+%Y-%m-%dT%H:%M:%S.%6N")
current_time_seconds=$(date -d "$current_time" +%s)
export INSTANCE_INIT_SECONDS=$(( current_time_seconds - created_time_seconds ))
echo "NOW_AT: $current_time"
echo "Init from Create: $INSTANCE_INIT_SECONDS seconds"
echo "---------------------------------------------------------------------------------"
printenv
echo "---------------------------------------------------------------------------------"
nvidia-smi
echo "---------------------------------------------------------------------------------"

# -------------------- common functions --------------------

download_conda(){
  echo "---------------------------------------------------------------------------------"
  echo "set conda environment..."
  mkdir -p /home/ubuntu/conda/lib/
  wget -qO /home/ubuntu/conda/lib/libcufft.so.10 https://huggingface.co/elonniu/esd/resolve/main/libcufft.so.10
  wget -qO /home/ubuntu/conda/lib/libcurand.so.10 https://huggingface.co/elonniu/esd/resolve/main/libcurand.so.10
}

find_and_remove_dir(){
  dir=$1
  name=$2
  echo "deleting dir $name in $dir ..."
  find "$dir" -type d \( -name "$name" \) | while read file; do
    remove_unused "$file";
  done
}

find_and_remove_file(){
  dir=$1
  name=$2
  echo "deleting file $name in $dir ..."
  find "$dir" -type f \( -name "$name" \) | while read file; do
    remove_unused "$file";
  done
}

remove_unused(){
  rm -rf "$1"
}

# -------------------- sd functions --------------------

sd_remove_unused_files(){
  echo "---------------------------------------------------------------------------------"
  echo "deleting unused files..."

  remove_unused /home/ubuntu/stable-diffusion-webui/extensions/stable-diffusion-aws-extension/docs
  remove_unused /home/ubuntu/stable-diffusion-webui/extensions/stable-diffusion-aws-extension/infrastructure
  remove_unused /home/ubuntu/stable-diffusion-webui/extensions/stable-diffusion-aws-extension/middleware_api
  remove_unused /home/ubuntu/stable-diffusion-webui/extensions/stable-diffusion-aws-extension/test
  remove_unused /home/ubuntu/stable-diffusion-webui/extensions/stable-diffusion-aws-extension/workshop

  remove_unused /home/ubuntu/stable-diffusion-webui/repositories/BLIP/BLIP.gif
  remove_unused /home/ubuntu/stable-diffusion-webui/repositories/generative-models/assets/
  remove_unused /home/ubuntu/stable-diffusion-webui/repositories/stable-diffusion-stability-ai/assets/

  find_and_remove_dir /home/ubuntu/stable-diffusion-webui ".git"
  find_and_remove_dir /home/ubuntu/stable-diffusion-webui ".github"

  find_and_remove_file /home/ubuntu/stable-diffusion-webui ".gitignore"
  find_and_remove_file /home/ubuntu/stable-diffusion-webui "CHANGELOG"
  find_and_remove_file /home/ubuntu/stable-diffusion-webui "CHANGELOG.md"
  find_and_remove_file /home/ubuntu/stable-diffusion-webui "README"
  find_and_remove_file /home/ubuntu/stable-diffusion-webui "README.md"
  find_and_remove_file /home/ubuntu/stable-diffusion-webui "NOTICE"
  find_and_remove_file /home/ubuntu/stable-diffusion-webui "NOTICE.md"
  find_and_remove_file /home/ubuntu/stable-diffusion-webui "CODE_OF_CONDUCT.md"
  find_and_remove_file /home/ubuntu/stable-diffusion-webui "LICENSE"
  find_and_remove_file /home/ubuntu/stable-diffusion-webui "LICENSE.md"
  find_and_remove_file /home/ubuntu/stable-diffusion-webui "LICENSE.txt"
  find_and_remove_file /home/ubuntu/stable-diffusion-webui "CODEOWNERS"
  find_and_remove_file /home/ubuntu/stable-diffusion-webui "*.jpg"
  find_and_remove_file /home/ubuntu/stable-diffusion-webui "*.png"
  find_and_remove_file /home/ubuntu/stable-diffusion-webui "*.gif"
}

sd_cache_endpoint() {
  start_at=$(date +%s)

  echo "collection big files..."
  upload_files=$(mktemp)
  big_files=$(find "/home/ubuntu/stable-diffusion-webui" -type f -size +2520k)
  for file in $big_files; do
    key=$(echo "$file" | cut -d'/' -f4-)
    echo "sync $file s3://$S3_BUCKET_NAME/$CACHE_ENDPOINT/$key" >> "$upload_files"
  done

  echo "tar files..."
  filelist=$(mktemp)
  # shellcheck disable=SC2164
  cd /home/ubuntu/stable-diffusion-webui
  find "./" \( -type f -o -type l \) -size -2530k > "$filelist"
  tar -cf $TAR_FILE -T "$filelist"

  echo "sync $TAR_FILE s3://$S3_BUCKET_NAME/$CACHE_ENDPOINT/" >> "$upload_files"
  echo "sync /home/ubuntu/conda/* s3://$S3_BUCKET_NAME/$CACHE_ENDPOINT/conda/" >> "$upload_files"

  # for ReActor
  echo "sync /home/ubuntu/stable-diffusion-webui/models/insightface/* s3://$S3_BUCKET_NAME/$CACHE_ENDPOINT/insightface/" >> "$upload_files"

  echo "upload files..."
  s5cmd run "$upload_files"

  end_at=$(date +%s)
  cost=$((end_at-start_at))
  echo "sync endpoint files: $cost seconds"
}

sd_build(){
  cd /home/ubuntu || exit 1
  bash install_sd.sh
}

sd_launch(){
  echo "---------------------------------------------------------------------------------"
  echo "accelerate sd launch..."

  echo "set conda environment..."
  export LD_LIBRARY_PATH=/home/ubuntu/conda/lib:$LD_LIBRARY_PATH

  ls -la /home/ubuntu/

  cd /home/ubuntu/stable-diffusion-webui || exit 1
  source venv/bin/activate

  python launch.py --enable-insecure-extension-access --api --api-log --log-startup --listen --port 8080 --xformers --no-half-vae --no-download-sd-model --no-hashing --nowebui --skip-torch-cuda-test --skip-load-model-at-start --disable-safe-unpickle --skip-prepare-environment --skip-python-version-check --skip-install --skip-version-check --disable-nan-check

   # python /controller.py
}

sd_launch_from_private_s3(){
    CACHE_PATH=$1
    start_at=$(date +%s)
    s5cmd --log=error sync "s3://$S3_BUCKET_NAME/$CACHE_PATH/*" /home/ubuntu/
    end_at=$(date +%s)
    cost=$((end_at-start_at))
    echo "download file: $cost seconds"

    start_at=$(date +%s)
    rm -rf /home/ubuntu/stable-diffusion-webui/models
    tar --overwrite -xf "$TAR_FILE" -C /home/ubuntu/stable-diffusion-webui/
    rm -rf $TAR_FILE
    end_at=$(date +%s)
    cost=$((end_at-start_at))
    echo "decompress file: $cost seconds"

    # remove soft link after decompress
    rm -rf /home/ubuntu/stable-diffusion-webui/models
    s5cmd --log=error sync "s3://$S3_BUCKET_NAME/$CACHE_PATH/insightface/*" "/home/ubuntu/stable-diffusion-webui/models/insightface/"

    cd /home/ubuntu/stable-diffusion-webui/ || exit 1

    mkdir -p models/VAE
    mkdir -p models/Stable-diffusion
    mkdir -p models/Lora
    mkdir -p models/hypernetworks

    sd_launch
}

sd_launch_from_public_s3(){
    CACHE_PATH=$1
    start_at=$(date +%s)
    s5cmd --log=error cp "s3://$CACHE_PATH" /home/ubuntu/
    end_at=$(date +%s)
    cost=$((end_at-start_at))
    echo "download file: $cost seconds"

    start_at=$(date +%s)
    tar --overwrite -xf "$SERVICE_TYPE.tar" -C /home/ubuntu/
    rm -rf "$SERVICE_TYPE.tar"
    end_at=$(date +%s)
    cost=$((end_at-start_at))
    echo "decompress file: $cost seconds"

    cd /home/ubuntu/stable-diffusion-webui/ || exit 1

    mkdir -p models/Lora
    mkdir -p models/hypernetworks

    if [ -z "$EXTENSIONS" ]; then
        echo "No extensions specified, just install the environment and launch from local..."
    fi

    sd_remove_unused_files
    sd_cache_endpoint
    sd_launch
}

# -------------------- comfy functions --------------------

comfy_remove_unused_files(){
  echo "---------------------------------------------------------------------------------"
  echo "deleting unused files..."

  find_and_remove_dir /home/ubuntu/ComfyUI ".git"
  find_and_remove_dir /home/ubuntu/ComfyUI ".github"

  find_and_remove_file /home/ubuntu/ComfyUI ".gitignore"
  find_and_remove_file /home/ubuntu/ComfyUI "README.md"
  find_and_remove_file /home/ubuntu/ComfyUI "CHANGELOG"
  find_and_remove_file /home/ubuntu/ComfyUI "CHANGELOG.md"
  find_and_remove_file /home/ubuntu/ComfyUI "CODE_OF_CONDUCT.md"
  find_and_remove_file /home/ubuntu/ComfyUI "NOTICE"
  find_and_remove_file /home/ubuntu/ComfyUI "NOTICE.md"
  find_and_remove_file /home/ubuntu/ComfyUI "CODEOWNERS"
  find_and_remove_file /home/ubuntu/ComfyUI "LICENSE"
  find_and_remove_file /home/ubuntu/ComfyUI "LICENSE.md"
  find_and_remove_file /home/ubuntu/ComfyUI "LICENSE.txt"
  find_and_remove_file /home/ubuntu/ComfyUI "*.gif"
  find_and_remove_file /home/ubuntu/ComfyUI "*.png"
  find_and_remove_file /home/ubuntu/ComfyUI "*.jpg"
}

comfy_build(){
  cd /home/ubuntu || exit 1
  bash install_comfy.sh
}

comfy_cache_endpoint() {
  start_at=$(date +%s)

  echo "collection big files..."
  upload_files=$(mktemp)
  big_files=$(find "/home/ubuntu/ComfyUI" -type f -size +2520k)
  for file in $big_files; do
    key=$(echo "$file" | cut -d'/' -f4-)
    echo "sync $file s3://$S3_BUCKET_NAME/$CACHE_ENDPOINT/$key" >> "$upload_files"
  done

  echo "tar files..."
  filelist=$(mktemp)
  # shellcheck disable=SC2164
  cd /home/ubuntu/ComfyUI
  find "./" \( -type f -o -type l \) -size -2530k > "$filelist"
  tar -cf $TAR_FILE -T "$filelist"

  echo "sync $TAR_FILE s3://$S3_BUCKET_NAME/$CACHE_ENDPOINT/" >> "$upload_files"
  echo "sync /home/ubuntu/conda/* s3://$S3_BUCKET_NAME/$CACHE_ENDPOINT/conda/" >> "$upload_files"

  echo "upload files..."
  s5cmd run "$upload_files"

  end_at=$(date +%s)
  cost=$((end_at-start_at))
  echo "sync endpoint files: $cost seconds"
}

comfy_launch(){
  echo "---------------------------------------------------------------------------------"
  echo "accelerate comfy launch..."

  echo "set conda environment..."
  export LD_LIBRARY_PATH=/home/ubuntu/conda/lib:$LD_LIBRARY_PATH

  cd /home/ubuntu/ComfyUI || exit 1
  rm /home/ubuntu/ComfyUI/custom_nodes/comfy_local_proxy.py
  source venv/bin/activate

  # python serve.py
  python /controller.py
}

comfy_launch_from_private_s3(){
    CACHE_PATH=$1
    start_at=$(date +%s)
    s5cmd --log=error sync "s3://$S3_BUCKET_NAME/$CACHE_PATH/*" /home/ubuntu/
    end_at=$(date +%s)
    cost=$((end_at-start_at))
    echo "download file: $cost seconds"

    start_at=$(date +%s)
    tar --overwrite -xf "$TAR_FILE" -C /home/ubuntu/ComfyUI/
    rm -rf $TAR_FILE
    end_at=$(date +%s)
    cost=$((end_at-start_at))
    echo "decompress file: $cost seconds"

    comfy_launch
}

comfy_launch_from_public_s3(){
    CACHE_PATH=$1
    start_at=$(date +%s)
    s5cmd --log=error cp "s3://$CACHE_PATH" /home/ubuntu/
    end_at=$(date +%s)
    cost=$((end_at-start_at))
    echo "download file: $cost seconds"

    start_at=$(date +%s)
    tar --overwrite -xf "$SERVICE_TYPE.tar" -C /home/ubuntu/
    rm -rf "$SERVICE_TYPE.tar"
    end_at=$(date +%s)
    cost=$((end_at-start_at))
    echo "decompress file: $cost seconds"

    comfy_remove_unused_files
    comfy_cache_endpoint
    comfy_launch
}

# -------------------- startup --------------------

if [ "$FULL_IMAGE" == "true" ]; then
  echo "Running on full docker image..."
  if [ "$SERVICE_TYPE" == "sd" ]; then
    sd_launch
    exit 1
  else
    comfy_launch
    exit 1
  fi
fi

output=$(s5cmd ls "s3://$S3_BUCKET_NAME/")

echo "Checking endpoint cache: s3://$S3_BUCKET_NAME/$CACHE_ENDPOINT"
if echo "$output" | grep -q "$CACHE_ENDPOINT"; then
  if [ "$SERVICE_TYPE" == "sd" ]; then
    sd_launch_from_private_s3 "$CACHE_ENDPOINT"
    exit 1
  else
    comfy_launch_from_private_s3 "$CACHE_ENDPOINT"
    exit 1
  fi
fi

echo "Checking public cache: s3://$CACHE_PUBLIC"
if [ "$SERVICE_TYPE" == "sd" ]; then
  sd_launch_from_public_s3 "$CACHE_PUBLIC"
  exit 1
else
  comfy_launch_from_public_s3 "$CACHE_PUBLIC"
  exit 1
fi

echo "No cache found in S3, just install the environment and launch from local..."
download_conda

if [ "$SERVICE_TYPE" == "sd" ]; then
    sd_build
    sd_remove_unused_files
    sd_cache_endpoint
    sd_launch
    exit 1
else
    comfy_build
    comfy_remove_unused_files
    comfy_cache_endpoint
    comfy_launch
    exit 1
fi
