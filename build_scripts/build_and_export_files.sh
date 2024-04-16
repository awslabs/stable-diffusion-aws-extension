#!/usr/bin/env bash

set -euxo pipefail

dockerfile=$1
tag_name=$2

curl -sSL "https://raw.githubusercontent.com/elonniu/s5cmd/main/install.sh" | bash > /dev/null 2>&1

echo "docker build $tag_name"
docker build --build-arg ESD_COMMIT_ID="$CODEBUILD_RESOLVED_SOURCE_VERSION" -t "$tag_name" -f "$dockerfile" .
docker images "$tag_name"

docker create --name "$tag_name" "$tag_name"
rm -rf  "/tmp/$tag_name"
mkdir -p "/tmp/$tag_name"
docker cp "$tag_name:/home/ubuntu" "/tmp/$tag_name/"
tar -cf "$tag_name.tar" -C "/tmp/$tag_name/ubuntu" . > /dev/null 2>&1
ls -la

mkdir -p ~/.aws
echo "[default]
region = $REGION" > ~/.aws/config

export AWS_REGION=$REGION
export AWS_DEFAULT_REGION=$REGION

bucket="aws-gcr-solutions-$REGION"
key="stable-diffusion-aws-extension-github-mainline/$BUILD_VERSION/$tag_name.tar"

s5cmd cp "$tag_name.tar" "s3://$bucket/$key"

aws s3api put-object-acl --region "$REGION" --bucket "$bucket" --key "$key" --acl public-read
