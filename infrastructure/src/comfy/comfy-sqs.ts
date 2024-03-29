import { Duration } from 'aws-cdk-lib';
import { AccountRootPrincipal, AnyPrincipal, Effect, PolicyStatement } from 'aws-cdk-lib/aws-iam';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import { Construct } from 'constructs';
import { SOLUTION_NAME } from '../shared/const';

export interface SqsProps {
  name: string;
  visibilityTimeout?: number;
}

export class SqsStack extends Construct {
  readonly queue: sqs.Queue;
  constructor(scope: Construct, id: string, props: SqsProps) {
    super(scope, id);

    this.queue = new sqs.Queue(scope, `${props.name}QueueActual`, {
      queueName: `${SOLUTION_NAME}-${props.name}.fifo`, //Name must be specified
      visibilityTimeout: Duration.seconds(props.visibilityTimeout ?? 30),
      encryption: sqs.QueueEncryption.SQS_MANAGED,
      contentBasedDeduplication: true,
    });
    this.queue.addToResourcePolicy(
      new PolicyStatement({
        effect: Effect.DENY,
        principals: [new AnyPrincipal()],
        actions: ['sqs:*'],
        resources: ['*'],
        conditions: {
          Bool: { 'aws:SecureTransport': 'false' },
        },
      }),
    );
    const myselfStatement = new PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'sqs:ReceiveMessage',
        'sqs:ChangeMessageVisibility',
        'sqs:GetQueueUrl',
        'sqs:DeleteMessage',
        'sqs:GetQueueAttributes',
        'sqs:SetQueueAttributes',
      ],
      resources: [this.queue.queueArn],
      principals: [new AccountRootPrincipal()],
    });
    this.queue.addToResourcePolicy(myselfStatement);
  }
}
