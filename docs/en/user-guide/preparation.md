# Connet Stable Diffusion WebUI with AWS Account

## Prerequisites
You need to have successfully completed the deployment of the solution.

## Steps
1. Visit [AWS CloudFormation Console](https://console.aws.amazon.com/cloudformation/){:target="_blank"}.
2. Select the root stack of the solution you created from stack list, rather than the nested stacks. The nested stacks will be indicated as 'NESTED' next to their names in the list.
3. Open **Outputs** tab, find URL of **APIGatewayUrl** and copy。
4. Open **Stable Diffusion WebUI**, nagivate to **Amazon SageMaker**tab，paste the URL copied from step 3 under **API URL**. Paste API token copied from step 3 into field of **API Token**. Click **Update Setting**，*config updated to local config!* message will appear. 
5. Click **Test Connection**, *Successfully Connected* message will appear, which indicates that Stable Diffusion WebUI has been successfully connected with AWS account of the backend deployed stack.
