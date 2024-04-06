#!/usr/bin/env bash

# Build inference image and push it to private ECR repository
dockerfile=$1
repo_name=$2
mode=$3
region=$4
tag=$5

if [ "$repo_name" = "" ] || [ "$dockerfile" = "" ]
then
    echo "Usage: $0 <docker-file> <image-name>"
    exit 1
fi

if [ "$tag" = "" ]
then
    tag=latest
fi

# Get the account number associated with the current IAM credentials
account=$(aws sts get-caller-identity --region "$region" --query Account --output text)

if [ $? -ne 0 ]
then
    exit 255
fi

if [[ $region == cn* ]]; then
    AWS_DOMAIN="amazonaws.com.cn"
else
    AWS_DOMAIN="amazonaws.com"
fi

# If the repository doesn't exist in ECR, create it.

desc_output=$(aws ecr describe-repositories --region "$region" --repository-names "$repo_name" 2>&1)

if [ $? -ne 0 ]
then
    if echo ${desc_output} | grep -q RepositoryNotFoundException
    then
        aws ecr create-repository --region "$region" --repository-name "$repo_name" > /dev/null
    else
        >&2 echo ${desc_output}
    fi
fi

aws ecr set-repository-policy --repository-name "$repo_name" --policy-text '{"Version": "2008-10-17", "Statement": [{"Sid": "public statement", "Effect": "Allow", "Principal": "*", "Action": ["ecr:BatchCheckLayerAvailability", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]}]}'

aws ecr get-login-password --region "$region" | docker login --username AWS --password-stdin "$account.dkr.ecr.$region.$AWS_DOMAIN"

# Build the docker image locally with the image name and then push it to ECR
# with the full name.
fullname="$account.dkr.ecr.$region.$AWS_DOMAIN/$repo_name:$tag"
echo "docker build $fullname"
docker build -t "$fullname" -f "$dockerfile" .

echo "docker push $fullname"
docker push "$fullname"
echo "docker push $fullname} Completed"
