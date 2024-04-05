#!/usr/bin/env bash

# This script shows how to build the Docker image and push it to ECR to be ready for use
# by Bracket.

# The argument to this script is the image name. This will be used as the image on the local
# machine and combined with the account and region to form the repository name for ECR.
dockerfile=$1
image=$2
mode=$3
tag=$4

# if AWS_DEFAULT_REGION start with cn, AWS_SUFIX == amazon.com.cn
if [[ $AWS_DEFAULT_REGION == cn* ]]; then
    AWS_DOMAIN="amazonaws.com.cn"
else
    AWS_DOMAIN="amazonaws.com"
fi

if [ "$image" = "" ] || [ "$dockerfile" = "" ]
then
    echo "Usage: $0 <docker-file> <image-name>"
    exit 1
fi

if [ -d "stable-diffusion-webui" ]; then
    echo "Removing existing project..."
    rm -rf stable-diffusion-webui
fi

if [ "$tag" = "" ]
then
    tag=latest
fi

# Get the account number associated with the current IAM credentials
account=$(aws sts get-caller-identity --query Account --output text)

if [ $? -ne 0 ]
then
    exit 255
fi

# Get the region defined in the current configuration (default to us-west-2 if none defined)
region=$(aws configure get region)
# region=${region:-us-west-2}

image_name="${image}"
fullname="${account}.dkr.ecr.${region}.${AWS_DOMAIN}/${image_name}:${tag}"

# If the repository doesn't exist in ECR, create it.

desc_output=$(aws ecr describe-repositories --repository-names ${image_name} 2>&1)

if [ $? -ne 0 ]
then
    if echo ${desc_output} | grep -q RepositoryNotFoundException
    then
        aws ecr create-repository --repository-name "${image_name}" > /dev/null
    else
        >&2 echo ${desc_output}
    fi
fi

aws ecr get-login-password --region ${region} | docker login -u AWS --password-stdin ${account}.dkr.ecr.${region}.${AWS_DOMAIN}

cp ${dockerfile} .

# Build the docker image locally with the image name and then push it to ECR
# with the full name.

docker build  -t ${fullname} -f ${dockerfile} .

# if docker build failed, exit
if [ $? -ne 0 ]
then
    echo "docker build failed"
    exit 255
fi

docker push ${fullname}

docker images $fullname
