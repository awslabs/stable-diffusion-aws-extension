import { Aws, CfnParameter } from 'aws-cdk-lib';
import {Topic} from 'aws-cdk-lib/aws-sns';
import { Construct } from 'constructs';
import { ResourceProvider } from './resource-provider';


export class SnsTopics {

  public readonly snsTopic: Topic;
  public readonly createModelSuccessTopic: Topic;
  public readonly createModelFailureTopic: Topic;
  public readonly inferenceResultTopic: Topic;
  public readonly inferenceResultErrorTopic: Topic;
  private readonly scope: Construct;
  private readonly id: string;
  private readonly resourceProvider: ResourceProvider;

  constructor(scope: Construct, id: string, emailParam: CfnParameter, resourceProvider: ResourceProvider) {

    this.scope = scope;
    this.id = id;
    this.resourceProvider = resourceProvider;

    // Check that props.emailParam and props.bucketName are not undefined
    if (!emailParam) {
      throw new Error('emailParam and bucketName must be provided');
    }

    // CDK parameters for SNS email address
    // Create SNS topic for notifications
    // const snsKmsKey = new kms.Key(this, 'SNSTrainEncryptionKey');
    // const newSnsKey = new aws_kms.Key(scope, `${id}-KmsMasterKey`, {
    //   enableKeyRotation: true,
    //   removalPolicy: RemovalPolicy.RETAIN,
    //   policy: new aws_iam.PolicyDocument({
    //     assignSids: true,
    //     statements: [
    //       new aws_iam.PolicyStatement({
    //         actions: ['kms:GenerateDataKey*', 'kms:Decrypt', 'kms:Encrypt'],
    //         resources: ['*'],
    //         effect: aws_iam.Effect.ALLOW,
    //         principals: [
    //           new aws_iam.ServicePrincipal('sns.amazonaws.com'),
    //           new aws_iam.ServicePrincipal('cloudwatch.amazonaws.com'),
    //           new aws_iam.ServicePrincipal('events.amazonaws.com'),
    //           new aws_iam.ServicePrincipal('sagemaker.amazonaws.com'),
    //         ],
    //       }),
    //       new aws_iam.PolicyStatement({
    //         actions: [
    //           'kms:Create*',
    //           'kms:Describe*',
    //           'kms:Enable*',
    //           'kms:List*',
    //           'kms:Put*',
    //           'kms:Update*',
    //           'kms:Revoke*',
    //           'kms:Disable*',
    //           'kms:Get*',
    //           'kms:Delete*',
    //           'kms:ScheduleKeyDeletion',
    //           'kms:CancelKeyDeletion',
    //           'kms:GenerateDataKey',
    //           'kms:TagResource',
    //           'kms:UntagResource',
    //         ],
    //         resources: ['*'],
    //         effect: aws_iam.Effect.ALLOW,
    //         principals: [new aws_iam.AccountRootPrincipal()],
    //       }),
    //     ],
    //   }),
    // });

    // (newSnsKey.node.defaultChild as aws_kms.CfnKey).cfnOptions.condition = shouldCreateSnsTopicCondition;
    // Subscribe user to SNS notifications
    // this.snsTopic.addSubscription(
    //   new sns_subscriptions.EmailSubscription(emailParam.valueAsString),
    // );

    // Create an SNS topic to get async inference result
    this.snsTopic = this.createOrImportTopic('StableDiffusionSnsUserTopic');
    this.inferenceResultTopic = this.createOrImportTopic('ReceiveSageMakerInferenceSuccess');
    this.inferenceResultErrorTopic = this.createOrImportTopic('ReceiveSageMakerInferenceError');
    this.createModelSuccessTopic = this.createOrImportTopic('successCreateModel');
    this.createModelFailureTopic = this.createOrImportTopic('failureCreateModel');
  }

  private static getTopicArnByTopicName(topicName: string): string {
    return `arn:${Aws.PARTITION}:sns:${Aws.REGION}:${Aws.ACCOUNT_ID}:${topicName}`;
  }

  private createOrImportTopic(topicName: string): Topic {

    const topic = <Topic>Topic.fromTopicArn(
      this.scope,
      `${this.id}-${topicName}`,
      SnsTopics.getTopicArnByTopicName(topicName),
    );

    topic.node.addDependency(this.resourceProvider.resources);

    return topic;
  }
}
