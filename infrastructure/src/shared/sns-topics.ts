import { Aws, CfnParameter } from 'aws-cdk-lib';
import { Topic } from 'aws-cdk-lib/aws-sns';
import { EmailSubscription } from 'aws-cdk-lib/aws-sns-subscriptions';
import { Construct } from 'constructs';


export class SnsTopics {

  public readonly snsTopic: Topic;
  public readonly inferenceResultTopic: Topic;
  public readonly inferenceResultErrorTopic: Topic;
  public readonly executeResultSuccessTopic: Topic;
  public readonly executeResultFailTopic: Topic;
  private readonly scope: Construct;
  private readonly id: string;

  constructor(scope: Construct, id: string, emailParam: CfnParameter) {

    this.scope = scope;
    this.id = id;

    // Create an SNS topic to get async inference result
    this.snsTopic = this.fromTopicArn('StableDiffusionSnsUserTopic');
    this.snsTopic.addSubscription(new EmailSubscription(emailParam.valueAsString));

    this.inferenceResultTopic = this.fromTopicArn('ReceiveSageMakerInferenceSuccess');
    this.inferenceResultErrorTopic = this.fromTopicArn('ReceiveSageMakerInferenceError');

    // comfy
    this.executeResultSuccessTopic = this.fromTopicArn('comfyExecuteSuccess');
    this.executeResultFailTopic = this.fromTopicArn('comfyExecuteFail');
  }

  private fromTopicArn(topicName: string): Topic {
    return <Topic>Topic.fromTopicArn(
      this.scope,
      `${this.id}-${topicName}`,
      `arn:${Aws.PARTITION}:sns:${Aws.REGION}:${Aws.ACCOUNT_ID}:${topicName}`,
    );
  }
}
