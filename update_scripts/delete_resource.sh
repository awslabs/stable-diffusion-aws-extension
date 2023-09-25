#!/bin/bash

# Clean all resources after removing the CloudFormation stack 
echo "Delete all sagemaker endpoints to avoid quota limitation"
# List SageMaker endpoints with names starting with "infer-endpoint"
endpoints=$(aws sagemaker list-endpoints --query "Endpoints[?starts_with(EndpointName, 'infer-endpoint')].EndpointName" --output text)

for endpoint_name in $endpoints; do
    echo "Deleting SageMaker endpoint: $endpoint_name"
    aws sagemaker delete-endpoint --endpoint-name "$endpoint_name"
done

echo "Remove all DynamoDB table"
for table in $(aws dynamodb list-tables --query 'TableNames[]' --output text); do aws dynamodb delete-table --table-name $table; done

echo "Remove solution's IAM role"
aws iam delete-role --role-name LambdaStartDeployRole

echo "Remove all SNS topic without sde-api-test-result"
topic_arns=$(aws sns list-topics --query 'Topics[].TopicArn' --output json)
for topic_arn in $(aws sns list-topics --query 'Topics[].TopicArn' --output text)
do
    aws sns delete-topic --topic-arn $topic_arn
done
