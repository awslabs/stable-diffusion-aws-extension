import { Aws, aws_iam, aws_kms, CfnCondition, CfnParameter, Fn, RemovalPolicy } from 'aws-cdk-lib';
import * as aws_sns from 'aws-cdk-lib/aws-sns';
import { Construct } from 'constructs';


export class SnsTopics {

  public readonly snsTopic: aws_sns.Topic;
  public readonly createModelSuccessTopic: aws_sns.Topic;
  public readonly createModelFailureTopic: aws_sns.Topic;
  public readonly inferenceResultTopic: aws_sns.Topic;
  public readonly inferenceResultErrorTopic: aws_sns.Topic;
  private readonly scope: Construct;
  private readonly id: string;

  constructor(scope: Construct, id: string, emailParam: CfnParameter, useExist: string) {

    this.scope = scope;
    this.id = id;

    // Check that props.emailParam and props.bucketName are not undefined
    if (!emailParam) {
      throw new Error('emailParam and bucketName must be provided');
    }


    const shouldCreateSnsTopicCondition = new CfnCondition(
      scope,
      `${id}-shouldCreateSnsTopic`,
      {
        expression: Fn.conditionEquals(useExist, 'no'),
      },
    );

    // CDK parameters for SNS email address
    // Create SNS topic for notifications
    // const snsKmsKey = new kms.Key(this, 'SNSTrainEncryptionKey');
    const newSnsKey = new aws_kms.Key(scope, `${id}-KmsMasterKey`, {
      enableKeyRotation: true,
      removalPolicy: RemovalPolicy.RETAIN,
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

    (newSnsKey.node.defaultChild as aws_kms.CfnKey).cfnOptions.condition = shouldCreateSnsTopicCondition;

    const newUserTopic = new aws_sns.Topic(scope, `${id}-NewStableDiffusionSnsTopic`, {
      masterKey: newSnsKey,
      topicName: 'StableDiffusionSnsUserTopic',
      displayName: 'StableDiffusionSnsUserTopic',
    });
    newUserTopic.applyRemovalPolicy(RemovalPolicy.RETAIN);
    (newUserTopic.node.defaultChild as aws_sns.CfnTopic).cfnOptions.condition = shouldCreateSnsTopicCondition;

    this.snsTopic = <aws_sns.Topic>aws_sns.Topic.fromTopicArn(scope, `${id}-StableDiffusionSnsTopic`, SnsTopics.getTopicArnByTopicName('StableDiffusionSnsUserTopic'));

    // Subscribe user to SNS notifications
    // this.snsTopic.addSubscription(
    //   new sns_subscriptions.EmailSubscription(emailParam.valueAsString),
    // );

    // Create an SNS topic to get async inference result
    this.inferenceResultTopic = this.createOrImportTopic('ReceiveSageMakerInferenceSuccess', shouldCreateSnsTopicCondition);
    this.inferenceResultErrorTopic = this.createOrImportTopic('ReceiveSageMakerInferenceError', shouldCreateSnsTopicCondition);
    this.createModelSuccessTopic = this.createOrImportTopic('successCreateModel', shouldCreateSnsTopicCondition);
    this.createModelFailureTopic = this.createOrImportTopic('failureCreateModel', shouldCreateSnsTopicCondition);
  }

  private static getTopicArnByTopicName(topicName: string): string {
    return `arn:${Aws.PARTITION}:sns:${Aws.REGION}:${Aws.ACCOUNT_ID}:${topicName}`;
  }

  private createOrImportTopic(topicName: string, useExistCondition: CfnCondition): aws_sns.Topic {
    const newTopic = new aws_sns.Topic(this.scope, `${this.id}-New${topicName}`, {
      topicName: topicName,
      displayName: topicName,
    });
    newTopic.applyRemovalPolicy(RemovalPolicy.RETAIN);
    (newTopic.node.defaultChild as aws_sns.CfnTopic).cfnOptions.condition = useExistCondition;
    return <aws_sns.Topic>aws_sns.Topic.fromTopicArn(this.scope, `${this.id}-${topicName}`, SnsTopics.getTopicArnByTopicName(topicName));
  }
}
