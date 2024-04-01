#!/bin/bash

DIR3="/home/ubuntu/ComfyUI/input"
DIR1="/home/ubuntu/ComfyUI/models"
DIR2="/home/ubuntu/ComfyUI/custom_nodes"

echo "listen start" > inotifywait.log

inotifywait -m -e modify,create,delete --format '%w %e' "$DIR1" "$DIR2" "$DIR3" |
    while read -r directory events; do
        echo "Directory changed: $directory Events: $events"
        echo "Directory changed: $directory Events: $events" >> inotifywait.log

        random_string=$(LC_ALL=C cat /dev/urandom | LC_ALL=C tr -dc 'a-z0-9' | fold -w 6 | head -n 1)
        echo "s5cmd sync $directory/* s3://$COMFY_BUCKET_NAME/comfy/$COMFY_ENDPOINT_NAME/$random_string/" >> inotifywait.log

        result=$(s5cmd sync "$directory/*" "s3://$COMFY_BUCKET_NAME/comfy/$COMFY_ENDPOINT_NAME/$random_string/")
        echo "$result" >> inotifywait.log

    done
