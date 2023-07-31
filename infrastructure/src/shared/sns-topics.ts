import { aws_iam, aws_kms, aws_sns, aws_sns_subscriptions as sns_subscriptions, CfnParameter } from 'aws-cdk-lib';
import { Construct } from 'constructs';

export class SnsTopics {
  public readonly snsTopic: aws_sns.Topic;

  constructor(scope: Construct, id: string, emailParam: CfnParameter) {
    // Check that props.emailParam and props.bucketName are not undefined
    if (!emailParam) {
      throw new Error('emailParam and bucketName must be provided');
    }

    // CDK parameters for SNS email address
    // Create SNS topic for notifications
    // const snsKmsKey = new kms.Key(this, 'SNSTrainEncryptionKey');
    const snsKey = new aws_kms.Key(scope, `${id}-KmsMasterKey`, {
      enableKeyRotation: true,
      policy: new aws_iam.PolicyDocument({
        assignSids: true,
        statements: [
          new aws_iam.PolicyStatement({
            actions: ['kms:GenerateDataKey*', 'kms:Decrypt', 'kms:Encrypt'],
            resources: ['*'],
            effect: aws_iam.Effect.ALLOW,
            principals: [
              new aws_iam.ServicePrincipal('sns.amazonaws.com'),
              new aws_iam.ServicePrincipal('cloudwatch.amazonaws.com'),
              new aws_iam.ServicePrincipal('events.amazonaws.com'),
              new aws_iam.ServicePrincipal('sagemaker.amazonaws.com'),
            ],
          }),
          new aws_iam.PolicyStatement({
            actions: [
              'kms:Create*',
              'kms:Describe*',
              'kms:Enable*',
              'kms:List*',
              'kms:Put*',
              'kms:Update*',
              'kms:Revoke*',
              'kms:Disable*',
              'kms:Get*',
              'kms:Delete*',
              'kms:ScheduleKeyDeletion',
              'kms:CancelKeyDeletion',
              'kms:GenerateDataKey',
              'kms:TagResource',
              'kms:UntagResource',
            ],
            resources: ['*'],
            effect: aws_iam.Effect.ALLOW,
            principals: [new aws_iam.AccountRootPrincipal()],
          }),
        ],
      }),
    });

    this.snsTopic = new aws_sns.Topic(scope, 'StableDiffusionSnsTopic', {
      masterKey: snsKey,
    });

    // Subscribe user to SNS notifications
    this.snsTopic.addSubscription(
      new sns_subscriptions.EmailSubscription(emailParam.valueAsString),
    );
  }
}