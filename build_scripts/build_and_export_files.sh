#!/usr/bin/env bash

set -euxo pipefail

export dockerfile=$1
export service_type=$2
export tag_name="$service_type-$REGION"
export container_name="$service_type-$REGION"

curl -sSL "https://raw.githubusercontent.com/elonniu/s5cmd/main/install.sh" | bash > /dev/null 2>&1

echo "docker build $tag_name"
docker build --build-arg ESD_COMMIT_ID="$CODEBUILD_RESOLVED_SOURCE_VERSION" -t "$tag_name" -f "$dockerfile" .
docker images "$tag_name"

docker rm "$container_name" || true
docker create --name "$container_name" "$tag_name"
rm -rf  "/tmp/$tag_name"
mkdir -p "/tmp/$tag_name"
docker cp "$container_name:/home/ubuntu" "/tmp/$tag_name/"
docker rm "$container_name" || true

rm -rf "$tag_name.tar"
tar -cf "$tag_name.tar" -C "/tmp/$tag_name/ubuntu" . > /dev/null 2>&1
ls -la "$tag_name.tar"

mkdir -p ~/.aws
echo "[default]
region = $REGION" > ~/.aws/config

export AWS_REGION=$REGION
export AWS_DEFAULT_REGION=$REGION

upload_file(){
  version=$1
  bucket="aws-gcr-solutions-$REGION"
  key="stable-diffusion-aws-extension-github-mainline/$version/$service_type.tar"

  s5cmd sync "$tag_name.tar" "s3://$bucket/$key"
  aws s3api put-object-acl --region "$REGION" --bucket "$bucket" --key "$key" --acl public-read
}

upload_file "dev"
upload_file "$BUILD_VERSION"
