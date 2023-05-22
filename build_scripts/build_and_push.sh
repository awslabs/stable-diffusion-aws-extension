#!/usr/bin/env bash

# This script shows how to build the Docker image and push it to ECR to be ready for use
# by Braket.

# The argument to this script is the image name. This will be used as the image on the local
# machine and combined with the account and region to form the repository name for ECR.
dockerfile=$1
image=$2
mode=$3

if [ "$image" = "" ] || [ "$dockerfile" = "" ]
then
    echo "Usage: $0 <docker-file> <image-name>"
    exit 1
fi

if [ -d "stable-diffusion-webui" ]; then
    echo "Removing existing project..."
    rm -rf stable-diffusion-webui
fi

# Sync github repo contents
cp ../install.sh .
sh install.sh
rm install.sh

if [ "$mode" = "dev" ]
then
    cd stable-diffusion-webui/extensions/stable-diffusion-aws-extension
    git checkout dev
    git pull
    cd -
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

image_name="stable-diffusion-aws-extension/${image}"
fullname="${account}.dkr.ecr.${region}.amazonaws.com/${image_name}:latest"

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

aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 763104351884.dkr.ecr.us-east-1.amazonaws.com
#aws ecr get-login-password --region us-west-2 | docker login -u AWS --password-stdin 292282985366.dkr.ecr.us-west-2.amazonaws.com
# aws ecr get-login-password --region ${region} | docker login -u AWS --password-stdin ${account}.dkr.ecr.${region}.amazonaws.com

cp ${dockerfile} .

# Build the docker image locally with the image name and then push it to ECR
# with the full name.

docker build  -t ${image_name} -f ${dockerfile} .
# docker tag ${image_name} ${fullname}

# docker push ${fullname}
# echo $fullname

# Push to public ecr
aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws/aws-gcr-solutions

# public_repo="initial"

# desc_output=$(aws ecr-public describe-repositories --repository-name ${image} --region us-east-1 2>&1)

# if echo ${desc_output} | grep -q RepositoryNotFoundException
# then
#         public_repo=$(aws ecr-public create-repository --repository-name ${image} --region us-east-1 | jq --raw-output '.repository.repositoryUri')
# else
#         public_repo=$(aws ecr-public describe-repositories --repository-name ${image} --region us-east-1 | jq --raw-output '.repositories[].repositoryUri')
# fi

# echo $public_repo

fullname="public.ecr.aws/aws-gcr-solutions/${image_name}:latest"
docker tag ${image_name}:latest ${fullname}
docker push ${fullname}
echo $fullname
