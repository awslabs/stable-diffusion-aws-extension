#!/bin/bash

set -euxo pipefail

CONTAINER_PATH=$(realpath ./container)
SUPERVISORD_FILE="$CONTAINER_PATH/supervisord.conf"

supervisorctl -c "$SUPERVISORD_FILE" shutdown || true

docker stop $(docker ps -q) || true

sudo rm -rf container

./docker_start.sh
