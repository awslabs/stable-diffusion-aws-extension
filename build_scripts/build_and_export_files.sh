#!/usr/bin/env bash

set -euxo pipefail

dockerfile=$1
tag_name=$2

curl -sSL "https://raw.githubusercontent.com/elonniu/s5cmd/main/install.sh" | bash;

echo "docker build $tag_name"
docker build --build-arg ESD_COMMIT_ID="$CODEBUILD_RESOLVED_SOURCE_VERSION" -t "$tag_name" -f "$dockerfile" .
docker images "$tag_name"

docker create --name file "$tag_name"
mkdir -p "/tmp/$tag_name"
docker cp file:/home/ubuntu "/tmp/$tag_name/"
tar -cf ubuntu.tar -C "/tmp/$tag_name/ubuntu" . > /dev/null 2>&1
ls -la
