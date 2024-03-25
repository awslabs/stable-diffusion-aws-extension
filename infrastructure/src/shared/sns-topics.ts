import { Aws, CfnParameter } from 'aws-cdk-lib';
import { Topic } from 'aws-cdk-lib/aws-sns';
import { EmailSubscription } from 'aws-cdk-lib/aws-sns-subscriptions';
import { Construct } from 'constructs';


export class SnsTopics {

  public readonly snsTopic: Topic;
  public readonly createModelSuccessTopic: Topic;
  public readonly createModelFailureTopic: Topic;
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
    this.snsTopic = this.createOrImportTopic('StableDiffusionSnsUserTopic');
    this.snsTopic.addSubscription(new EmailSubscription(emailParam.valueAsString));

    this.inferenceResultTopic = this.createOrImportTopic('ReceiveSageMakerInferenceSuccess');
    this.inferenceResultErrorTopic = this.createOrImportTopic('ReceiveSageMakerInferenceError');
    this.createModelSuccessTopic = this.createOrImportTopic('successCreateModel');
    this.createModelFailureTopic = this.createOrImportTopic('failureCreateModel');
    this.executeResultSuccessTopic = this.createOrImportTopic('sageMakerExecuteSuccess');
    this.executeResultFailTopic = this.createOrImportTopic('sageMakerExecuteFail');

  }

  private createOrImportTopic(topicName: string): Topic {
    return <Topic>Topic.fromTopicArn(
      this.scope,
      `${this.id}-${topicName}`,
      `arn:${Aws.PARTITION}:sns:${Aws.REGION}:${Aws.ACCOUNT_ID}:${topicName}`,
    );
  }
}
