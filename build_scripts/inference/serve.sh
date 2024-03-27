#!/bin/bash

if [ -z "$ESD_VERSION" ]; then
  echo "ESD_VERSION is not set"
  exit 1
fi

export ESD_CODE_BRANCH="main"
export WEBUI_PORT=8080
export TAR_FILE="webui.tar"
export S3_LOCATION="esd-$INSTANCE_TYPE-$ESD_VERSION"

if [[ $IMAGE_URL == *"dev"* ]]; then
  export ESD_CODE_BRANCH="dev"
  # Enable dev mode
  trap 'echo "error_lock" > /error_lock; exit 1' ERR
  if [ -f "/error_lock" ]; then
      echo "start failed, please check the log"
      sleep 30
      exit 1
  fi
fi

if [ -n "$EXTENSIONS" ]; then
    export S3_LOCATION="$ENDPOINT_NAME-$ESD_VERSION"
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
init_seconds=$(( current_time_seconds - created_time_seconds ))
echo "NOW_AT: $current_time"
echo "Init from Create: $init_seconds seconds"
echo "---------------------------------------------------------------------------------"
printenv
echo "---------------------------------------------------------------------------------"
nvidia-smi
echo "---------------------------------------------------------------------------------"

install_esd(){
  echo "---------------------------------------------------------------------------------"
  echo "install esd..."

  cd /home/ubuntu || exit 1

  curl -sSL "https://raw.githubusercontent.com/awslabs/stable-diffusion-aws-extension/$ESD_CODE_BRANCH/install.sh" | bash;

  # if $EXTENSIONS is not empty, it will be executed
  if [ -n "$EXTENSIONS" ]; then
      echo "---------------------------------------------------------------------------------"
      echo "install extensions..."
      cd /home/ubuntu/stable-diffusion-webui/extensions/ || exit 1

      read -ra array <<< "$(echo "$EXTENSIONS" | tr "," " ")"

      for git_repo in "${array[@]}"; do
        IFS='#' read -r -a repo <<< "$git_repo"

        git_repo=${repo[0]}
        repo_name=$(basename -s .git "$git_repo")
        repo_branch=${repo[1]}
        commit_sha=${repo[2]}

        echo "rm -rf $repo_name for install $git_repo"
        rm -rf $repo_name

        start_at=$(date +%s)

        echo "git clone $git_repo"
        git clone "$git_repo"

        cd $repo_name || exit 1

        echo "git checkout $repo_branch"
        git checkout "$repo_branch"

        echo "git reset --hard $commit_sha"
        git reset --hard "$commit_sha"
        cd ..

        end_at=$(date +%s)
        cost=$((end_at-start_at))
        echo "git clone $git_repo: $cost seconds"
      done
  fi
}

remove_unused(){
  echo "rm $1"
  rm -rf "$1"
}

remove_unused_list(){
  echo "---------------------------------------------------------------------------------"
  echo "deleting big unused files..."
  remove_unused /home/ubuntu/stable-diffusion-webui/extensions/stable-diffusion-aws-extension/docs
  remove_unused /home/ubuntu/stable-diffusion-webui/extensions/stable-diffusion-aws-extension/infrastructure
  remove_unused /home/ubuntu/stable-diffusion-webui/extensions/stable-diffusion-aws-extension/middleware_api
  remove_unused /home/ubuntu/stable-diffusion-webui/extensions/stable-diffusion-aws-extension/test
  remove_unused /home/ubuntu/stable-diffusion-webui/repositories/BLIP/BLIP.gif
  remove_unused /home/ubuntu/stable-diffusion-webui/repositories/generative-models/assets/
  remove_unused /home/ubuntu/stable-diffusion-webui/repositories/stable-diffusion-stability-ai/assets/

  echo "deleting git dir..."
  find /home/ubuntu/stable-diffusion-webui -type d \( -name '.git' -o -name '.github' \) | while read dir; do
    remove_unused "$dir";
  done

  echo "deleting unused files..."
  find /home/ubuntu/stable-diffusion-webui -type f \( -name '.gitignore' -o -name 'README.md' -o -name 'CHANGELOG.md' \) | while read file; do
    remove_unused "$file";
  done

  find /home/ubuntu/stable-diffusion-webui -type f \( -name 'CODE_OF_CONDUCT.md' -o -name 'LICENSE.md' -o -name 'NOTICE.md' \) | while read file; do
    remove_unused "$file";
  done

  find /home/ubuntu/stable-diffusion-webui -type f \( -name 'CODEOWNERS' -o -name 'LICENSE.txt' -o -name 'LICENSE' \) | while read file; do
    remove_unused "$file";
  done

  find /home/ubuntu/stable-diffusion-webui -type f \( -name '*.gif' -o -name '*.png' -o -name '*.jpg' \) | while read file; do
    remove_unused "$file";
  done
}

listen_ready() {
  while true; do
    RESPONSE_CODE=$(curl -o /dev/null -s -w "%{http_code}\n" localhost:8080/ping)
    if [ "$RESPONSE_CODE" -eq 200 ]; then
        echo "Server is ready!"

        start_at=$(date +%s)

        echo "collection big files..."
        upload_files=$(mktemp)
        big_files=$(find "/home/ubuntu/stable-diffusion-webui" -type f -size +2520k)
        for file in $big_files; do
          key=$(echo "$file" | cut -d'/' -f4-)
          echo "sync $file s3://$BUCKET_NAME/$S3_LOCATION/$key" >> "$upload_files"
        done

        echo "tar files..."
        filelist=$(mktemp)
        # shellcheck disable=SC2164
        cd /home/ubuntu/stable-diffusion-webui
        find "./" \( -type f -o -type l \) -size -2530k > "$filelist"
        tar -cf $TAR_FILE -T "$filelist"

        echo "sync $TAR_FILE s3://$BUCKET_NAME/$S3_LOCATION/" >> "$upload_files"
        echo "sync /home/ubuntu/conda/* s3://$BUCKET_NAME/$S3_LOCATION/conda/" >> "$upload_files"

        # for ReActor
        echo "sync /home/ubuntu/stable-diffusion-webui/models/insightface/* s3://$BUCKET_NAME/$S3_LOCATION/insightface/" >> "$upload_files"

        echo "upload files..."
        s5cmd run "$upload_files"

        end_at=$(date +%s)
        cost=$((end_at-start_at))
        echo "sync endpoint files: $cost seconds"
      break
    fi

    sleep 2
  done
}

set_conda(){
  echo "---------------------------------------------------------------------------------"
  echo "set conda environment..."
  export AWS_REGION="us-west-2"
  conda_path="aws-gcr-solutions-us-west-2/extension-for-stable-diffusion-on-aws/1.5.0-g5/conda"
  s5cmd --log=error cp "s3://$conda_path/libcufft.so.10" /home/ubuntu/conda/lib/
  s5cmd --log=error cp "s3://$conda_path/libcurand.so.10" /home/ubuntu/conda/lib/
  export LD_LIBRARY_PATH=/home/ubuntu/conda/lib:$LD_LIBRARY_PATH
  export AWS_REGION=$AWS_DEFAULT_REGION
}

build_for_launch(){
  install_esd

  echo "---------------------------------------------------------------------------------"
  echo "creating venv and install packages..."
  cd /home/ubuntu/stable-diffusion-webui || exit 1

  python3 -m venv venv

  source venv/bin/activate

  python -m pip install --upgrade pip
  python -m pip install onnxruntime-gpu
  python -m pip install insightface==0.7.3

  export TORCH_INDEX_URL="https://download.pytorch.org/whl/cu118"
  export TORCH_COMMAND="pip install torch==2.0.1 torchvision==0.15.2 --extra-index-url $TORCH_INDEX_URL"
  export XFORMERS_PACKAGE="xformers==0.0.20"

  echo "---------------------------------------------------------------------------------"
  echo "build for launch..."
  python launch.py --enable-insecure-extension-access --api --api-log --log-startup --listen --port $WEBUI_PORT --xformers --no-half-vae --no-download-sd-model --no-hashing --nowebui --skip-torch-cuda-test --skip-load-model-at-start --disable-safe-unpickle --disable-nan-check --exit
}

accelerate_launch(){
  echo "---------------------------------------------------------------------------------"
  echo "accelerate launch..."
  cd /home/ubuntu/stable-diffusion-webui || exit 1
  source venv/bin/activate
  accelerate launch --num_cpu_threads_per_process=$CUP_CORE_NUMS launch.py --enable-insecure-extension-access --api --api-log --log-startup --listen --port $WEBUI_PORT --xformers --no-half-vae --no-download-sd-model --no-hashing --nowebui --skip-torch-cuda-test --skip-load-model-at-start --disable-safe-unpickle --skip-prepare-environment --skip-python-version-check --skip-install --skip-version-check --disable-nan-check
}

launch_from_s3(){
    start_at=$(date +%s)
    s5cmd --log=error sync "s3://$BUCKET_NAME/$S3_LOCATION/*" /home/ubuntu/
    end_at=$(date +%s)
    cost=$((end_at-start_at))
    echo "download file: $cost seconds"

    echo "set conda environment..."
    export LD_LIBRARY_PATH=/home/ubuntu/conda/lib:$LD_LIBRARY_PATH

    start_at=$(date +%s)
    tar --overwrite -xf "webui.tar" -C /home/ubuntu/stable-diffusion-webui/
    rm -rf $TAR_FILE
    end_at=$(date +%s)
    cost=$((end_at-start_at))
    echo "decompress file: $cost seconds"

    # remove soft link
    rm -rf /home/ubuntu/stable-diffusion-webui/models
    s5cmd --log=error sync "s3://$BUCKET_NAME/$S3_LOCATION/insightface/*" "/home/ubuntu/stable-diffusion-webui/models/insightface/"

    cd /home/ubuntu/stable-diffusion-webui/ || exit 1

    mkdir -p models/VAE
    mkdir -p models/Stable-diffusion
    mkdir -p models/Lora
    mkdir -p models/hypernetworks

    accelerate_launch
}

launch_from_local(){
  set_conda
  build_for_launch
  remove_unused_list
  listen_ready &
  accelerate_launch
}

echo "Checking s3://$BUCKET_NAME/$S3_LOCATION files..."
output=$(s5cmd ls "s3://$BUCKET_NAME/")
if echo "$output" | grep -q "$S3_LOCATION"; then
  launch_from_s3
fi

echo "No files in S3, just install the environment and launch from local..."
launch_from_local
