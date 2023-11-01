#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

ENDPOINT_NAME=$1
if [ -z "$ENDPOINT_NAME" ]
then
    echo "Usage: $0 <endpoint-name> <new-image-uri>"
    exit 1
fi

NEW_IMAGE_URI=$2
if [ -z "$NEW_IMAGE_URI" ]
then
    echo "Usage: $0 <endpoint-name> <new-image-uri>"
    exit 1
fi

# if os is centos, install jq
if [ -f /etc/redhat-release ]; then
    sudo yum install -y jq
fi

# if os is ubuntu, install jq
if [ -f /etc/lsb-release ]; then
    sudo apt install -y jq
fi

# Describe the existing endpoint to get the endpoint configuration name
ENDPOINT_CONFIG_NAME=$(aws sagemaker describe-endpoint --endpoint-name $ENDPOINT_NAME --query 'EndpointConfigName' --output text)
echo "Endpoint configuration name: $ENDPOINT_CONFIG_NAME"

# Describe the existing endpoint configuration to get the details
CONFIG_DETAILS=$(aws sagemaker describe-endpoint-config --endpoint-config-name "$ENDPOINT_CONFIG_NAME")

# Extract model name, variant name, instance type, AsyncInferenceConfig, and Environment
MODEL_NAME=$(echo "$CONFIG_DETAILS" | jq -r '.ProductionVariants[0].ModelName')
echo "Model name: $MODEL_NAME"

# Extract model name and environment
MODEL_DETAIlS=$(aws sagemaker describe-model --model-name "$MODEL_NAME")

VARIANT_NAME=$(echo "$CONFIG_DETAILS" | jq -r '.ProductionVariants[0].VariantName')
echo "Variant name: $VARIANT_NAME"

INSTANCE_TYPE=$(echo "$CONFIG_DETAILS" | jq -r '.ProductionVariants[0].InstanceType')
echo "Instance type: $INSTANCE_TYPE"

INITIAL_INSTANCE_COUNT=$(echo "$CONFIG_DETAILS" | jq -r '.ProductionVariants[0].InitialInstanceCount')
echo "Initial instance count: $INITIAL_INSTANCE_COUNT"

INITIAL_VARIANT_WEIGHT=$(echo "$CONFIG_DETAILS" | jq -r '.ProductionVariants[0].InitialVariantWeight')
echo "Initial variant weight: $INITIAL_VARIANT_WEIGHT"

S3OutputPath=$(echo "$CONFIG_DETAILS" | jq -r '.AsyncInferenceConfig.OutputConfig.S3OutputPath')
echo "S3OutputPath: $S3OutputPath"

SuccessTopic=$(echo "$CONFIG_DETAILS" | jq -r '.AsyncInferenceConfig.OutputConfig.NotificationConfig.SuccessTopic')
echo "SuccessTopic: $SuccessTopic"

ErrorTopic=$(echo "$CONFIG_DETAILS" | jq -r '.AsyncInferenceConfig.OutputConfig.NotificationConfig.ErrorTopic')
echo "ErrorTopic: $ErrorTopic"

EndpointID=$(echo "$MODEL_DETAIlS" | jq -r '.PrimaryContainer.Environment.EndpointID')
echo "EndpointID: $EndpointID"

MODEL_DATA_URL=$(echo "$MODEL_DETAIlS" | jq -r '.PrimaryContainer.ModelDataUrl')
echo "Model data URL: $MODEL_DATA_URL"

MODEL_EXECUTION_ROLE_ARN=$(echo "$MODEL_DETAIlS" | jq -r '.ExecutionRoleArn')
echo "Model execution role ARN: $MODEL_EXECUTION_ROLE_ARN"

# Delete the existing endpoint (this will result in downtime)
aws sagemaker delete-endpoint --endpoint-name $ENDPOINT_NAME | jq

echo "Waiting for endpoint to be deleted..."
aws sagemaker wait endpoint-deleted --endpoint-name $ENDPOINT_NAME | jq

echo "Deleting existing model..."
aws sagemaker delete-model --model-name "$MODEL_NAME" | jq

echo  "Deleting existing endpoint configuration..."
aws sagemaker delete-endpoint-config --endpoint-config-name "$ENDPOINT_CONFIG_NAME" | jq

## Create a new model with the new image URI
echo  "Recreating model..."
aws sagemaker create-model \
    --model-name "${MODEL_NAME}" \
    --execution-role-arn "$MODEL_EXECUTION_ROLE_ARN" \
    --primary-container "{
        \"Image\": \"$NEW_IMAGE_URI\",
        \"ModelDataUrl\": \"$MODEL_DATA_URL\",
        \"Environment\": {
          \"EndpointID\": \"$EndpointID\"
        }
      }" | jq

## Create a new endpoint configuration with the same name but new model
echo "Recreating endpoint configuration..."
aws sagemaker create-endpoint-config \
    --endpoint-config-name "$ENDPOINT_CONFIG_NAME" \
    --production-variants VariantName="$VARIANT_NAME",ModelName="$MODEL_NAME",InstanceType="$INSTANCE_TYPE",InitialInstanceCount=1 \
    --async-inference-config "{\"OutputConfig\":{\"S3OutputPath\":\"${S3OutputPath}\",\"NotificationConfig\":{\"SuccessTopic\":\"${SuccessTopic}\",\"ErrorTopic\":\"${ErrorTopic}\"}}}" | jq

## Create a new endpoint with the same name
echo "Recreating endpoint..."
aws sagemaker create-endpoint \
    --endpoint-name "$ENDPOINT_NAME" \
    --endpoint-config-name "$ENDPOINT_CONFIG_NAME" | jq

echo "Waiting for endpoint to be created..."
aws sagemaker wait endpoint-in-service --endpoint-name "$ENDPOINT_NAME" | jq
