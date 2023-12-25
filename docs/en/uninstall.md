# Uninstall Extension for Stable Diffusion on AWS 

!!! Warning "Warning"
    Before uninstalling the solution, please manually delete all the Amazon SageMaker Endpoints deployed by this solution, referring to **Delete deployed endpoint** in [Main tab](./user-guide/CloudAssetsManage.md). By uninstalling the solution, the DynamoDB tables that indicate the model training, finetuning and inference logs and mapping relationship, AWS Lambda related functions, AWS Step Functions and so on will be deleted simultaneously.


To uninstall the Extension for Stable Diffusion on AWS solution, you must delete the AWS CloudFormation stack. 

You can use either the AWS Management Console or the AWS Command Line Interface (AWS CLI) to delete the CloudFormation stack.

## Uninstall the stack using the AWS Management Console

1. Sign in to the [AWS CloudFormation][cloudformation-console] console.
1. Select this solution’s installation parent stack.
1. Choose **Delete**.

## Uninstall the stack using AWS Command Line Interface

Determine whether the AWS Command Line Interface (AWS CLI) is available in your environment. For installation instructions, refer to [What Is the AWS Command Line Interface][aws-cli] in the *AWS CLI User Guide*. After confirming that the AWS CLI is available, run the following command.

```bash
aws cloudformation delete-stack --stack-name <installation-stack-name> --region <aws-region>
```


[cloudformation-console]: https://console.aws.amazon.com/cloudformation/home
[aws-cli]: https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-welcome.html
