#!/bin/bash

echo "cancel temp"
exit 0

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
  echo "removing $1 ..."
  rm -rf "$1"
}

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
