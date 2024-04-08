#!/bin/bash

echo "---------------------------------------------------------------------------------"
echo "install esd..."

export INITIAL_SUPPORT_COMMIT_ROOT=bef51aed032c0aaa5cfd80445bc4cf0d85b408b5
export INITIAL_SUPPORT_COMMIT_CONTROLNET=2a210f0489a4484f55088159bbfa51aaf73e10d9
export INITIAL_SUPPORT_COMMIT_TILEDVAE=f9f8073e64f4e682838f255215039ba7884553bf
export INITIAL_SUPPORT_COMMIT_REMBG=a4c07b857e73f3035f759876797fa6de986def3d
export INITIAL_SUPPORT_COMMIT_REACTOR=0185d7a2afa4a3c76b304314233a1cafd1cf4842

rm -rf stable-diffusion-webui

# Clone stable-diffusion-webui
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git --branch master --single-branch
# Go to stable-diffusion-webui directory
cd stable-diffusion-webui || exit 1
# Reset to specific commit
git reset --hard ${INITIAL_SUPPORT_COMMIT_ROOT}

# Go to "extensions" directory
cd extensions || exit 1

# Clone stable-diffusion-aws-extension
git clone https://github.com/awslabs/stable-diffusion-aws-extension.git --branch "dev" --single-branch
cd stable-diffusion-aws-extension || exit 1

# remove unused files for docker layer reuse
rm -rf docs
rm -rf infrastructure
rm -rf middleware_api
rm -rf test
rm -rf workshop

if [ -n "$ESD_COMMIT_ID" ]; then
  echo "reset ESD to $ESD_COMMIT_ID"
  git reset --hard "$ESD_COMMIT_ID"
fi

cd ../

# Clone sd-webui-controlnet
git clone https://github.com/Mikubill/sd-webui-controlnet.git --branch main --single-branch
# Go to sd-webui-controlnet directory and reset to specific commit
cd sd-webui-controlnet || exit 1
git reset --hard ${INITIAL_SUPPORT_COMMIT_CONTROLNET}
cd ../

# Clone Tiled VAE
git clone https://github.com/pkuliyi2015/multidiffusion-upscaler-for-automatic1111.git --branch main --single-branch
cd multidiffusion-upscaler-for-automatic1111 || exit 1
git reset --hard ${INITIAL_SUPPORT_COMMIT_TILEDVAE}
cd ../

git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui-rembg.git --branch master --single-branch
cd stable-diffusion-webui-rembg || exit 1
git reset --hard ${INITIAL_SUPPORT_COMMIT_REMBG}
cd ../

# Clone sd-webui-reactor
git clone https://github.com/Gourieff/sd-webui-reactor.git --branch main --single-branch
# Go to reactor directory and reset to specific commit
cd sd-webui-reactor || exit 1
git reset --hard ${INITIAL_SUPPORT_COMMIT_REACTOR}
cd ../

# if $EXTENSIONS is not empty, it will be executed
if [ -n "$EXTENSIONS" ]; then
    echo "---------------------------------------------------------------------------------"
    echo "install extensions..."

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
fi

echo "---------------------------------------------------------------------------------"
echo "build esd..."

cd ../

python3 -m venv venv

source venv/bin/activate

pip install --upgrade pip
pip install onnxruntime-gpu
pip install insightface==0.7.3
pip install boto3
pip install aws_xray_sdk

export TORCH_INDEX_URL="https://download.pytorch.org/whl/cu118"
export TORCH_COMMAND="pip install torch==2.0.1 torchvision==0.15.2 --extra-index-url $TORCH_INDEX_URL"
export XFORMERS_PACKAGE="xformers==0.0.20"

echo "---------------------------------------------------------------------------------"
echo "build for launch..."
python launch.py --enable-insecure-extension-access --api --api-log --log-startup --listen --xformers --no-half-vae --no-download-sd-model --no-hashing --nowebui --skip-torch-cuda-test --skip-load-model-at-start --disable-safe-unpickle --disable-nan-check --exit
