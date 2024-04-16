#!/bin/bash

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
