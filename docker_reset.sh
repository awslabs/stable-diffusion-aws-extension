#!/bin/bash

set -euxo pipefail


SUPERVISORD_FILE="$CONTAINER_PATH/supervisord.conf"

supervisorctl -c "$SUPERVISORD_FILE" shutdown || true

git pull

rm -rf container/

reboot

exit 1
