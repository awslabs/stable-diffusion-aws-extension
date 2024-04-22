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

# Use verified cache version file for production: v1.5.0-fe21616
export CACHE_PUBLIC_SD="aws-gcr-solutions-$AWS_REGION/stable-diffusion-aws-extension-github-mainline/$ESD_VERSION/sd.tar"

# Use verified cache version file for production: v1.5.0-fe21616
export CACHE_PUBLIC_COMFY="aws-gcr-solutions-$AWS_REGION/stable-diffusion-aws-extension-github-mainline/$ESD_VERSION/comfy.tar"

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

set_conda(){
    echo "set conda environment..."
    export LD_LIBRARY_PATH=/home/ubuntu/conda/lib:$LD_LIBRARY_PATH
}

download_conda(){
  echo "---------------------------------------------------------------------------------"
  echo "downloading conda ..."
  mkdir -p /home/ubuntu/conda/lib/
  wget -qO /home/ubuntu/conda/lib/libcufft.so.10 https://huggingface.co/elonniu/esd/resolve/main/libcufft.so.10
  wget -qO /home/ubuntu/conda/lib/libcurand.so.10 https://huggingface.co/elonniu/esd/resolve/main/libcurand.so.10
  set_conda
}

# -------------------- sd functions --------------------

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

  echo "upload files..."
  s5cmd run "$upload_files"

  end_at=$(date +%s)
  cost=$((end_at-start_at))
  echo "sync endpoint files: $cost seconds"
}

sd_install_build(){
  cd /home/ubuntu || exit 1
  bash install_sd.sh
}

sd_launch(){
  echo "---------------------------------------------------------------------------------"
  echo "accelerate sd launch..."

  set_conda

  ls -la /home/ubuntu/

  mkdir -p /root/.u2net/
  mv /home/ubuntu/stable-diffusion-webui/u2net_human_seg.onnx /root/.u2net/

  if [[ $AWS_REGION == *"cn-"* ]]; then
    mkdir -p /root/.cache/huggingface/accelerate
    mv /home/ubuntu/stable-diffusion-webui/default_config.yaml /root/.cache/huggingface/accelerate/
  fi

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
    tar --overwrite -xf "$TAR_FILE" -C /home/ubuntu/stable-diffusion-webui/
    rm -rf $TAR_FILE
    end_at=$(date +%s)
    cost=$((end_at-start_at))
    echo "decompress file: $cost seconds"

    cd /home/ubuntu/stable-diffusion-webui/ || exit 1

    mkdir -p models/Lora || true
    mkdir -p models/hypernetworks || true
    mkdir -p models/ControlNet || true

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

    # if $EXTENSIONS is not empty, it will be executed
    if [ -n "$EXTENSIONS" ]; then
        echo "---------------------------------------------------------------------------------"
        echo "install extensions..."

        cd extensions || exit 1

        read -ra array <<< "$(echo "$EXTENSIONS" | tr "," " ")"

        for git_repo in "${array[@]}"; do
          IFS='#' read -r -a repo <<< "$git_repo"

          git_repo=${repo[0]}
          repo_name=$(basename -s .git "$git_repo")
          repo_branch=${repo[1]}
          commit_sha=${repo[2]}

          echo "rm -rf $repo_name for install $git_repo"
          rm -rf "$repo_name"

          start_at=$(date +%s)

          echo "git clone $git_repo"
          git clone "$git_repo"

          cd "$repo_name" || exit 1

          echo "git checkout $repo_branch"
          git checkout "$repo_branch"

          echo "git reset --hard $commit_sha"
          git reset --hard "$commit_sha"
          cd ..

          end_at=$(date +%s)
          cost=$((end_at-start_at))
          echo "git clone $git_repo: $cost seconds"
        done

        cd /home/ubuntu/stable-diffusion-webui/ || exit 1
        echo "---------------------------------------------------------------------------------"
        echo "build for launch..."
        python launch.py --enable-insecure-extension-access --api --api-log --log-startup --listen --xformers --no-half-vae --no-download-sd-model --no-hashing --nowebui --skip-torch-cuda-test --skip-load-model-at-start --disable-safe-unpickle --disable-nan-check --exit
    fi

    cd /home/ubuntu/stable-diffusion-webui/ || exit 1

    /trim_sd.sh
    sd_cache_endpoint
    sd_launch
}

# -------------------- comfy functions --------------------

comfy_install_build(){
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

  set_conda

  cd /home/ubuntu/ComfyUI || exit 1
  rm /home/ubuntu/ComfyUI/custom_nodes/comfy_local_proxy.py
  source venv/bin/activate

   python serve.py
#  python /controller.py
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

    /trim_comfy.sh
    comfy_cache_endpoint
    comfy_launch
}

# -------------------- startup --------------------

if [[ $IMAGE_URL == *"dev"* ]]; then
  download_conda
  if [ "$SERVICE_TYPE" == "sd" ]; then
      sd_install_build
      /trim_sd.sh
      sd_cache_endpoint
      sd_launch
      exit 1
  else
      comfy_install_build
      /trim_comfy.sh
#      comfy_cache_endpoint
      comfy_launch
      exit 1
  fi
fi

#output=$(s5cmd ls "s3://$S3_BUCKET_NAME/")
#if echo "$output" | grep -q "$CACHE_ENDPOINT"; then
#  echo "Use endpoint cache: s3://$S3_BUCKET_NAME/$CACHE_ENDPOINT"
#  if [ "$SERVICE_TYPE" == "sd" ]; then
#    sd_launch_from_private_s3 "$CACHE_ENDPOINT"
#    exit 1
#  else
#    comfy_launch_from_private_s3 "$CACHE_ENDPOINT"
#    exit 1
#  fi
#fi
#
#if [ "$SERVICE_TYPE" == "sd" ]; then
#  echo "Use public cache: s3://$CACHE_PUBLIC_SD"
#  sd_launch_from_public_s3 "$CACHE_PUBLIC_SD"
#  exit 1
#else
#  echo "Use public cache: s3://$CACHE_PUBLIC_COMFY"
#  comfy_launch_from_public_s3 "$CACHE_PUBLIC_COMFY"
#  exit 1
#fi
