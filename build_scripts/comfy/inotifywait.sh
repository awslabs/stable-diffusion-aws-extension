#!/bin/bash

source /etc/environment

DIR3="/ComfyUI/input"
DIR1="/ComfyUI/models"
DIR2="/ComfyUI/custom_nodes"

echo "listen start"

sync_files(){
  directory=$1
  events=$2
  echo "Files changed in: $directory Events: $events"
  timestamp=$(date +%s%3N)
  s5cmd sync "/ComfyUI/input/*" "s3://$COMFY_BUCKET_NAME/comfy/$COMFY_ENDPOINT/$timestamp/input/"
  s5cmd sync "/ComfyUI/models/*" "s3://$COMFY_BUCKET_NAME/comfy/$COMFY_ENDPOINT/$timestamp/models/"
  s5cmd sync "/ComfyUI/custom_nodes/*" "s3://$COMFY_BUCKET_NAME/comfy/$COMFY_ENDPOINT/$timestamp/custom_nodes/"
}

inotifywait -m -e modify,create,delete --format '%w %e' "$DIR1" "$DIR2" "$DIR3" |
    while read -r directory events; do
        sync_files "$directory" "$events"
    done
