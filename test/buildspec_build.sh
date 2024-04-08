set -euxo pipefail

export STACK_NAME="Extension-for-Stable-Diffusion-on-AWS"
export ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
export API_BUCKET=esd-test-$ACCOUNT_ID-$AWS_DEFAULT_REGION

if [ "$CLEAN_RESOURCES" = "yes" ]; then
   export API_BUCKET=esd-test-$ACCOUNT_ID-$AWS_DEFAULT_REGION-$CODEBUILD_BUILD_NUMBER
fi

echo "export ACCOUNT_ID=$ACCOUNT_ID" > env.properties
echo "export API_BUCKET=$API_BUCKET" >> env.properties
echo "export STACK_NAME=$STACK_NAME" >> env.properties

aws cloudformation delete-stack --stack-name "$STACK_NAME"

python --version
sudo yum install wget -y

echo "----------------------------------------------------------------"
echo "$DEPLOY_STACK deploy start..."
echo "----------------------------------------------------------------"
STARTED_TIME=$(date +%s)
if [ "$DEPLOY_STACK" = "cdk" ]; then
   pushd "stable-diffusion-aws-extension/infrastructure"
   npm i -g pnpm
   pnpm i
   npx cdk synth --output cdk.out
   aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME"
   aws cloudformation deploy --stack-name "$STACK_NAME" \
                             --template-file cdk.out/Extension-for-Stable-Diffusion-on-AWS.template.json \
                             --capabilities CAPABILITY_NAMED_IAM \
                             --parameter-overrides Email="example@example.com" \
                                                   Bucket="$API_BUCKET" \
                                                   LogLevel=="INFO" \
                                                   SdExtensionApiKey=="09876743210987654322"
   popd
else
   aws cloudformation create-stack --stack-name "$STACK_NAME" \
                                   --template-url "$TEMPLATE_FILE" \
                                   --capabilities CAPABILITY_NAMED_IAM \
                                   --parameters ParameterKey=Email,ParameterValue="example@example.com" \
                                                ParameterKey=Bucket,ParameterValue="$API_BUCKET" \
                                                ParameterKey=LogLevel,ParameterValue="INFO" \
                                                ParameterKey=SdExtensionApiKey,ParameterValue="09876743210987654322"
   aws cloudformation wait stack-create-complete --stack-name "$STACK_NAME"
fi
FINISHED_TIME=$(date +%s)
export DEPLOY_DURATION_TIME=$(( $FINISHED_TIME - $STARTED_TIME ))
echo "export DEPLOY_DURATION_TIME=$DEPLOY_DURATION_TIME" >> env.properties

echo "----------------------------------------------------------------"
echo "Get api gateway url & token"
echo "----------------------------------------------------------------"
stack_info=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME")
export API_GATEWAY_URL=$(echo "$stack_info" | jq -r '.Stacks[0].Outputs[] | select(.OutputKey=="ApiGatewayUrl").OutputValue')
export API_GATEWAY_URL_TOKEN=$(echo "$stack_info" | jq -r '.Stacks[0].Outputs[] | select(.OutputKey=="ApiGatewayUrlToken").OutputValue')
echo "export API_GATEWAY_URL=$API_GATEWAY_URL" >> env.properties
echo "export API_GATEWAY_URL_TOKEN=$API_GATEWAY_URL_TOKEN" >> env.properties

cd stable-diffusion-aws-extension/test
make build

echo "----------------------------------------------------------------"
echo "Running pytest..."
echo "----------------------------------------------------------------"
API_TEST_STARTED_TIME=$(date +%s)
echo "export API_TEST_STARTED_TIME=$API_TEST_STARTED_TIME" >> env.properties
source venv/bin/activate
pytest ./ --exitfirst -rA --log-cli-level="INFO" --json-report --json-report-summary --json-report-file=detailed_report.json --html="report-${CODEBUILD_BUILD_NUMBER}.html" --self-contained-html --continue-on-collection-errors
FINISHED_TIME=$(date +%s)
