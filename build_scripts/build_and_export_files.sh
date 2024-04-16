#!/usr/bin/env bash

set -euxo pipefail

dockerfile=$1
tag_name=$2

curl -sSL "https://raw.githubusercontent.com/elonniu/s5cmd/main/install.sh" | bash > /dev/null 2>&1

echo "docker build $tag_name"
docker build --build-arg ESD_COMMIT_ID="$CODEBUILD_RESOLVED_SOURCE_VERSION" -t "$tag_name" -f "$dockerfile" .
docker images "$tag_name"

docker create --name file "$tag_name"
rm -rf  "/tmp/$tag_name"
mkdir -p "/tmp/$tag_name"
docker cp file:/home/ubuntu "/tmp/$tag_name/"
tar -cf ubuntu.tar -C "/tmp/$tag_name/ubuntu" . > /dev/null 2>&1
ls -la

mkdir -p ~/.aws
echo "[default]
region = $REGION" > ~/.aws/config

s5cmd cp ubuntu.tar "s3://aws-gcr-solutions-$REGION/stable-diffusion-aws-extension-github-mainline/$BUILD_VERSION/ubuntu.tar"
