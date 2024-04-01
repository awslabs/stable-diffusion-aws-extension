#!/bin/bash

DIR3="/home/ubuntu/ComfyUI/input"
DIR1="/home/ubuntu/ComfyUI/models"
DIR2="/home/ubuntu/ComfyUI/custom_nodes"

inotifywait -m -e modify,create,delete --format '%w %e' "$DIR1" "$DIR2" "$DIR3" |
    while read -r directory events; do
        echo "Directory changed: $directory Events: $events"
    done
