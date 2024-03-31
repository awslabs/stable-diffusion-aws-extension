#!/usr/bin/env bash

dockerfile=$1
image=$2
mode=$3
tag=$4
commit_id=$5
image_path=$6

if [ "$image" = "" ] || [ "$dockerfile" = "" ]
then
    echo "Usage: $0 <docker-file> <image-name>"
    exit 1
fi

if [ "$mode" = "" ]
then
    git clone https://github.com/comfyanonymous/ComfyUI.git
    cd ComfyUI
    git checkout master
    git pull
    cd -
else
    git checkout $mode
    git pull
    if [ -n "$commit_id" ]
    then
        git reset --hard $commit_id
        echo `git rev-parse HEAD`
    fi
fi

if [ "$tag" = "" ]
then
    tag=latest
fi

account=$(aws sts get-caller-identity --query Account --output text)

if [ $? -ne 0 ]
then
    exit 255
fi

region=$(aws configure get region)

if [ -n "$image_path" ]
then
  image_name="$image_path/${image}"
else
  image_name="gen-ai-common-aws-extension/${image}"
fi

fullname="${account}.dkr.ecr.${region}.amazonaws.com/${image_name}:${tag}"

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

cp ${dockerfile} .

docker build  -t ${image_name}:${tag} -f ${dockerfile} .

aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws/aws-gcr-solutions

fullname="public.ecr.aws/aws-gcr-solutions/${image_name}:${tag}"
docker tag ${image_name}:${tag} ${fullname}
docker push ${fullname}
echo $fullname
