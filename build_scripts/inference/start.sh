#!/bin/bash

#set -euxo pipefail

arch

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

export ENDPOINT_INSTANCE_ID=$(date +"%m%d%H%M%S")

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
df -h
echo "---------------------------------------------------------------------------------"

# -------------------- common functions --------------------

set_conda(){
    echo "set conda environment..."
    export LD_LIBRARY_PATH=/home/ubuntu/conda/lib:$LD_LIBRARY_PATH
}

download_conda(){
  echo "---------------------------------------------------------------------------------"
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
  export UPLOAD_ENDPOINT_CACHE_SECONDS=$((end_at-start_at))
  echo "sync endpoint files: $UPLOAD_ENDPOINT_CACHE_SECONDS seconds"
}

sd_install_build(){
  cd /home/ubuntu || exit 1
  bash install_sd.sh
}

sd_launch_cmd(){
  python launch.py --enable-insecure-extension-access --api --api-log --log-startup --listen --port 8080 --xformers --no-half-vae --no-download-sd-model --no-hashing --nowebui --skip-torch-cuda-test --skip-load-model-at-start --disable-safe-unpickle --skip-prepare-environment --skip-python-version-check --skip-install --skip-version-check --disable-nan-check
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

  echo "initiated_lock" > /initiated_lock

  cd /home/ubuntu/stable-diffusion-webui || exit 1
  chmod -R +x venv/bin

  source venv/bin/activate
  python /metrics.py &

  sd_launch_cmd
}

sd_launch_from_private_s3(){
    start_at=$(date +%s)
    s5cmd sync "s3://$S3_BUCKET_NAME/$CACHE_ENDPOINT/*" /home/ubuntu/
    end_at=$(date +%s)
    export DOWNLOAD_FILE_SECONDS=$((end_at-start_at))
    echo "download file: $DOWNLOAD_FILE_SECONDS seconds"

    export DOWNLOAD_FILE_SIZE=$(du -sm /home/ubuntu | awk '{print $1}' | grep -oE '[0-9]+')

    start_at=$(date +%s)
    tar --overwrite -xf "$TAR_FILE" -C /home/ubuntu/stable-diffusion-webui/
    rm -rf $TAR_FILE
    end_at=$(date +%s)
    export DECOMPRESS_SECONDS=$((end_at-start_at))
    echo "decompress file: $DECOMPRESS_SECONDS seconds"

    cd /home/ubuntu/stable-diffusion-webui/ || exit 1

    mkdir -p models/Lora || true
    mkdir -p models/hypernetworks || true
    mkdir -p models/ControlNet || true

    sd_launch
}

sd_launch_from_public_s3(){
    start_at=$(date +%s)
    s5cmd cp "s3://$CACHE_PUBLIC_SD" /home/ubuntu/
    end_at=$(date +%s)
    export DOWNLOAD_FILE_SECONDS=$((end_at-start_at))
    echo "download file: $DOWNLOAD_FILE_SECONDS seconds"

    export DOWNLOAD_FILE_SIZE=$(du -sm /home/ubuntu | awk '{print $1}' | grep -oE '[0-9]+')

    start_at=$(date +%s)
    tar --overwrite -xf "$SERVICE_TYPE.tar" -C /home/ubuntu/
    rm -rf "$SERVICE_TYPE.tar"
    end_at=$(date +%s)
    export DECOMPRESS_SECONDS=$((end_at-start_at))
    echo "decompress file: $DECOMPRESS_SECONDS seconds"

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

    /serve trim_sd
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

  s5cmd run "$upload_files"

  end_at=$(date +%s)
  export UPLOAD_ENDPOINT_CACHE_SECONDS=$((end_at-start_at))
  echo "sync endpoint files: $UPLOAD_ENDPOINT_CACHE_SECONDS seconds"
}

comfy_launch(){
  echo "---------------------------------------------------------------------------------"
  echo "accelerate comfy launch..."

  set_conda

  cd /home/ubuntu/ComfyUI || exit 1
  chmod -R +x venv/bin

  rm -rf /home/ubuntu/ComfyUI/custom_nodes/ComfyUI-AWS-Extension
  rm /home/ubuntu/ComfyUI/custom_nodes/comfy_local_proxy.py
  source venv/bin/activate
  python /metrics.py &

  echo "initiated_lock" > /initiated_lock

  python serve.py
}

comfy_launch_from_private_s3(){
    start_at=$(date +%s)
    s5cmd sync "s3://$S3_BUCKET_NAME/$CACHE_ENDPOINT/*" /home/ubuntu/
    end_at=$(date +%s)
    export DOWNLOAD_FILE_SECONDS=$((end_at-start_at))
    echo "download file: $DOWNLOAD_FILE_SECONDS seconds"

    export DOWNLOAD_FILE_SIZE=$(du -sm /home/ubuntu | awk '{print $1}' | grep -oE '[0-9]+')

    start_at=$(date +%s)
    tar --overwrite -xf "$TAR_FILE" -C /home/ubuntu/ComfyUI/
    rm -rf $TAR_FILE
    end_at=$(date +%s)
    export DECOMPRESS_SECONDS=$((end_at-start_at))
    echo "decompress file: $DECOMPRESS_SECONDS seconds"

    comfy_launch
}

comfy_launch_from_public_s3(){
    start_at=$(date +%s)
    s5cmd cp "s3://$CACHE_PUBLIC_COMFY" /home/ubuntu/
    end_at=$(date +%s)
    export DOWNLOAD_FILE_SECONDS=$((end_at-start_at))
    echo "download file: $DOWNLOAD_FILE_SECONDS seconds"

    export DOWNLOAD_FILE_SIZE=$(du -sm /home/ubuntu | awk '{print $1}' | grep -oE '[0-9]+')

    start_at=$(date +%s)
    tar --overwrite -xf "$SERVICE_TYPE.tar" -C /home/ubuntu/
    rm -rf "$SERVICE_TYPE.tar"
    end_at=$(date +%s)
    export DECOMPRESS_SECONDS=$((end_at-start_at))
    echo "decompress file: $DECOMPRESS_SECONDS seconds"

    /serve trim_comfy
    comfy_cache_endpoint
    comfy_launch
}

# -------------------- startup --------------------

# if pipeline finished, it will be executed
#if [[ $IMAGE_URL == *"dev"* ]]; then
#  download_conda
#  if [ "$SERVICE_TYPE" == "sd" ]; then
#      sd_install_build
#      /serve trim_sd.sh
#      sd_cache_endpoint
#      sd_launch
#      exit 1
#  else
#      comfy_install_build
#      /serve trim_comfy
#      comfy_cache_endpoint
#      comfy_launch
#      exit 1
#  fi
#fi

ec2_start_process(){
  set -euxo pipefail
  echo "---------------------------------------------------------------------------------"
  export LD_LIBRARY_PATH=$LD_PRELOAD
  download_conda
  init_port=8187
  for i in $(seq 1 "$PROCESS_NUMBER"); do
      init_port=$((init_port + 1))

      if [ "$init_port" -eq "8188" ]; then
          MASTER_PROCESS=true
      else
          MASTER_PROCESS=false
      fi

      if [ "$i" -eq "$PROCESS_NUMBER" ]; then
          export MASTER_PROCESS=$MASTER_PROCESS && python3 main.py --listen 0.0.0.0 \
                                                        --port "$init_port" \
                                                        --cuda-malloc \
                                                        --output-directory "/home/ubuntu/ComfyUI/output/$init_port" \
                                                        --temp-directory "/home/ubuntu/ComfyUI/temp/$init_port"
          exit 1
      fi

      export MASTER_PROCESS=$MASTER_PROCESS && nohup python3 main.py --listen 0.0.0.0 \
                                            --port "$init_port" \
                                            --cuda-malloc \
                                            --output-directory "/home/ubuntu/ComfyUI/output/$init_port" \
                                            --temp-directory "/home/ubuntu/ComfyUI/temp/$init_port" &
  done
}

if [ -n "$COMFY_EC2" ]; then
  set -euxo pipefail
  cd /home/ubuntu || exit 1

  if [ -d "/home/ubuntu/ComfyUI/venv" ]; then
      cd /home/ubuntu/ComfyUI || exit 1
      rm -rf web/extensions/ComfyLiterals
      chmod -R +x venv
      source venv/bin/activate
      ec2_start_process
      exit 1
  fi

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

  wget --quiet -O models/checkpoints/v1-5-pruned-emaonly.ckpt "https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.ckpt"

  chmod -R 777 /home/ubuntu/ComfyUI

  ec2_start_process

  exit 1
fi

if [ -n "$APP_SOURCE" ]; then
  if [ -n "$APP_CWD" ]; then
    start_at=$(date +%s)
    s5cmd --log=error sync "s3://$S3_BUCKET_NAME/${APP_SOURCE}*" "$APP_CWD"
    end_at=$(date +%s)
    export DOWNLOAD_FILE_SECONDS=$((end_at-start_at))
    echo "download file: $DOWNLOAD_FILE_SECONDS seconds"

    cd "$APP_CWD" || exit 1

    rm -rf web/extensions/ComfyLiterals

    chmod -R 777 "$APP_CWD"
    chmod -R +x venv

    source venv/bin/activate

    python3 serve.py

    exit 1
  fi
fi

if [ -f "/initiated_lock" ]; then
    echo "already initiated, start service directly..."
    if [ "$SERVICE_TYPE" == "sd" ]; then
      cd /home/ubuntu/stable-diffusion-webui || exit 1
      chmod -R +x venv/bin
      source venv/bin/activate
      sd_launch_cmd
      exit 1
    else
      cd /home/ubuntu/ComfyUI || exit 1
      chmod -R +x venv/bin
      source venv/bin/activate
      python serve.py
      exit 1
    fi
fi

output=$(s5cmd ls "s3://$S3_BUCKET_NAME/")
if echo "$output" | grep -q "$CACHE_ENDPOINT"; then
  if [ "$SERVICE_TYPE" == "sd" ]; then
    sd_launch_from_private_s3
    exit 1
  else
    comfy_launch_from_private_s3
    exit 1
  fi
fi

if [ "$SERVICE_TYPE" == "sd" ]; then
  sd_launch_from_public_s3
  exit 1
else
  comfy_launch_from_public_s3
  exit 1
fi
