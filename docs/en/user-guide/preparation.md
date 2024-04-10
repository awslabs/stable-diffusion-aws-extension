# Connect Stable Diffusion WebUI with AWS Account

## Prerequisites

You need to have successfully completed the deployment of the solution.

## Steps

1. Visit [AWS CloudFormation Console](https://console.aws.amazon.com/cloudformation/){:target="_blank"}.
2. Select the root stack of the solution you created from a stack list.
3. Open **Outputs** tab, find URL of **APIGatewayUrl** and copy。
4. Open **Stable Diffusion WebUI**, navigate to **Amazon SageMaker**tab，paste the URL copied from step 3 under **API URL
   **. Paste API token copied from step 3 into field of **API Token**. Click **Update Setting**，*config updated to local
   config!* message will appear.
5. Click **Test Connection & Update Setting**.
