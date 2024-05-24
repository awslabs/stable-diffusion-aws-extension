#!/bin/bash

set -euxo pipefail

if [ -f "/etc/environment" ]; then
    source /etc/environment
fi

export SERVICE_TYPE="comfy"
export CONTAINER_NAME="esd_container"
export ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
export AWS_REGION=$(aws configure get region)

CONTAINER_PATH=$(realpath ./container)
SUPERVISORD_FILE="$CONTAINER_PATH/supervisord.conf"

# Check if the repository already exists
if aws ecr describe-repositories --region "$AWS_REGION" --repository-names "$CONTAINER_NAME" >/dev/null 2>&1; then
    echo "ECR repository '$CONTAINER_NAME' already exists."
else
    echo "ECR repository '$CONTAINER_NAME' does not exist. Creating..."
    aws ecr create-repository --repository-name --region "$AWS_REGION" "$CONTAINER_NAME" | jq .
    echo "ECR repository '$CONTAINER_NAME' created successfully."
fi

aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "366590864501.dkr.ecr.$AWS_REGION.amazonaws.com"
PUBLIC_BASE_IMAGE="366590864501.dkr.ecr.$AWS_REGION.amazonaws.com/esd-inference:$ESD_VERSION"
docker pull "$PUBLIC_BASE_IMAGE"

export release_image="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$CONTAINER_NAME"

echo "Starting container..."
# local vol can be replace with your local directory
local_volume="./container/$SERVICE_TYPE"
mkdir -p $local_volume

if [ -n "${WORKFLOW_NAME-}" ]; then
    echo "WORKFLOW_NAME is $WORKFLOW_NAME"
else
   export WORKFLOW_NAME=""
fi

total_memory=$(cat /proc/meminfo | grep 'MemTotal' | awk '{print $2}')
total_memory_mb=$((total_memory / 1024))
echo "total_memory_mb: $total_memory_mb"
export limit_memory_mb=$((total_memory_mb - 2048))
echo "limit_memory_mb: $limit_memory_mb"

generate_process(){
  init_port=$1
  export PROGRAM_NAME="comfy_$init_port"
  comfy_workflow_file="./container/$PROGRAM_NAME"

  WORKFLOW_NAME_TMP=""

  if [ -f "$comfy_workflow_file" ]; then
    WORKFLOW_NAME_TMP=$(cat "$comfy_workflow_file")
  fi

  if [ -z "$WORKFLOW_NAME_TMP" ]; then
    WORKFLOW_NAME_TMP="$WORKFLOW_NAME"
  fi

  if [ -z "$WORKFLOW_NAME_TMP" ]; then
    WORKFLOW_NAME_TMP="default"
  fi

  echo "$WORKFLOW_NAME_TMP" > "$comfy_workflow_file"

  export MASTER_PROCESS=false
  if [ "$init_port" -eq "8188" ]; then
      export MASTER_PROCESS=true
  fi

  DOCKER_FILE="ARG BASE_IMAGE
FROM \$BASE_IMAGE

#RUN apt-get update -y && \
#    apt-get install ffmpeg -y && \
#    rm -rf /var/lib/apt/lists/*

WORKDIR /home/ubuntu/ComfyUI"

  if [ ! -f "./container/$PROGRAM_NAME.Dockerfile" ]; then
    echo "$DOCKER_FILE" > "./container/$PROGRAM_NAME.Dockerfile"
  fi

  START_SH=$(realpath ./build_scripts/inference/start.sh)
  COMFY_PROXY=$(realpath ./build_scripts/comfy/comfy_proxy.py)
  AWS_PATH=$(realpath ~/.aws)
  START_HANDLER="#!/bin/bash
set -euxo pipefail

WORKFLOW_NAME=\$(cat ./container/$PROGRAM_NAME)

BASE_IMAGE=$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$CONTAINER_NAME:\$WORKFLOW_NAME

if [ \"\$WORKFLOW_NAME\" = \"default\" ]; then
  BASE_IMAGE=$PUBLIC_BASE_IMAGE
else
  aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
  docker pull $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/esd_container:\"\$WORKFLOW_NAME\"
fi

docker build -f ./container/$PROGRAM_NAME.Dockerfile --build-arg BASE_IMAGE=\"\$BASE_IMAGE\" -t $PROGRAM_NAME .
docker stop $PROGRAM_NAME || true
docker rm $PROGRAM_NAME || true
docker run -v $AWS_PATH:/root/.aws \\
           -v $CONTAINER_PATH:/container \\
           -v $START_SH:/start.sh \\
           -v $COMFY_PROXY:/comfy_proxy.py \\
           --gpus all \\
           -e IMAGE_HASH=$release_image \\
           -e SERVICE_TYPE=$SERVICE_TYPE \\
           -e ON_EC2=true \\
           -e S3_BUCKET_NAME=$COMFY_BUCKET_NAME \\
           -e AWS_REGION=$AWS_REGION \\
           -e AWS_DEFAULT_REGION=$AWS_REGION \\
           -e COMFY_API_URL=$COMFY_API_URL \\
           -e COMFY_API_TOKEN=$COMFY_API_TOKEN \\
           -e ESD_VERSION=$ESD_VERSION \\
           -e COMFY_BUCKET_NAME=$COMFY_BUCKET_NAME \\
           -e MASTER_PROCESS=$MASTER_PROCESS \\
           -e PROGRAM_NAME=$PROGRAM_NAME \\
           -e WORKFLOW_NAME_FILE=/container/$PROGRAM_NAME \\
           --name $PROGRAM_NAME \\
           -p $init_port:8188 \\
           --memory ${limit_memory_mb}mb \\
           $PROGRAM_NAME"

  echo "$START_HANDLER" > "$CONTAINER_PATH/$PROGRAM_NAME.sh"
  chmod +x "$CONTAINER_PATH/$PROGRAM_NAME.sh"

  # shellcheck disable=SC2129
  echo "[program:$PROGRAM_NAME]" >> "$SUPERVISORD_FILE"
  echo "command=$CONTAINER_PATH/$PROGRAM_NAME.sh" >> "$SUPERVISORD_FILE"
  echo "startretries=2" >> "$SUPERVISORD_FILE"
  echo "stdout_logfile=$CONTAINER_PATH/$PROGRAM_NAME.stdout.log" >> "$SUPERVISORD_FILE"
  echo "stderr_logfile=$CONTAINER_PATH/$PROGRAM_NAME.stderr.log" >> "$SUPERVISORD_FILE"
  echo "" >> "$SUPERVISORD_FILE"
}


echo "---------------------------------------------------------------------------------"

SUPERVISOR_CONF="[supervisord]
nodaemon=true
autostart=true
autorestart=true

[inet_http_server]
port=127.0.0.1:9001

[rpcinterface:supervisor]
supervisor.rpcinterface_factory=supervisor.rpcinterface:make_main_rpcinterface

[supervisorctl]
logfile=/dev/stdout
"

echo "$SUPERVISOR_CONF" > "$SUPERVISORD_FILE"

echo "[program:image]" >> "$SUPERVISORD_FILE"
echo "command=./docker_image.sh" >> "$SUPERVISORD_FILE"
echo "startretries=1" >> "$SUPERVISORD_FILE"
echo "stdout_logfile=$CONTAINER_PATH/image.stdout.log" >> "$SUPERVISORD_FILE"
echo "stderr_logfile=$CONTAINER_PATH/image.stderr.log" >> "$SUPERVISORD_FILE"
echo "" >> "$SUPERVISORD_FILE"

init_port=8187
for i in $(seq 1 "$PROCESS_NUMBER"); do
    init_port=$((init_port + 1))
    generate_process $init_port
done

supervisorctl -c "$SUPERVISORD_FILE" shutdown || true

supervisord -c "$SUPERVISORD_FILE" | grep -v 'uncaptured python exception'

exit 1
