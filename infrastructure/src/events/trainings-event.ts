import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, aws_iam, aws_s3, aws_sns, CfnParameter, Duration } from 'aws-cdk-lib';
import { Table } from 'aws-cdk-lib/aws-dynamodb';
import { Rule } from 'aws-cdk-lib/aws-events';
import { LambdaFunction } from 'aws-cdk-lib/aws-events-targets';
import { Effect, PolicyStatement, Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';
import { Architecture, LayerVersion, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';

export interface SagemakerTrainingEventsProps {
  trainingTable: Table;
  checkpointTable: Table;
  srcRoot: string;
  commonLayer: LayerVersion;
  userTopic: aws_sns.Topic;
  s3Bucket: aws_s3.Bucket;
  logLevel: CfnParameter;
}

export class SagemakerTrainingEvents {
  private readonly src: string;
  private readonly scope: Construct;
  private readonly trainingTable: Table;
  private readonly checkpointTable: Table;
  private readonly layer: LayerVersion;
  private readonly baseId: string;
  private readonly userSnsTopic: aws_sns.Topic;
  private readonly s3Bucket: aws_s3.Bucket;
  private readonly logLevel: CfnParameter;


  constructor(scope: Construct, id: string, props: SagemakerTrainingEventsProps) {
    this.scope = scope;
    this.baseId = id;
    this.trainingTable = props.trainingTable;
    this.checkpointTable = props.checkpointTable;
    this.src = props.srcRoot;
    this.layer = props.commonLayer;
    this.userSnsTopic = props.userTopic;
    this.s3Bucket = props.s3Bucket;
    this.logLevel = props.logLevel;

    this.createTrainingEventsBridge();
  }

  private iamRole(): Role {

    const newRole = new Role(this.scope, `${this.baseId}-role`, {
      assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
    });

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'dynamodb:UpdateItem',
        'dynamodb:Scan',
        'dynamodb:GetItem',
      ],
      resources: [
        this.trainingTable.tableArn,
        this.checkpointTable.tableArn,
      ],
    }));

    newRole.addToPolicy(new PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'sagemaker:DeleteEndpoint',
        'sagemaker:DescribeEndpoint',
        'sagemaker:DescribeEndpointConfig',
        'sagemaker:UpdateEndpointWeightsAndCapacities',
        'cloudwatch:DeleteAlarms',
        'cloudwatch:DescribeAlarms',
        'cloudwatch:PutMetricAlarm',
        'application-autoscaling:PutScalingPolicy',
        'application-autoscaling:RegisterScalableTarget',
      ],
      resources: ['*'],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'sns:Publish',
        'sns:GetTopicAttributes',
        'sns:SetTopicAttributes',
        'sns:Subscribe',
        'sns:ListSubscriptionsByTopic',
        'sns:Receive',
      ],
      resources: [this.userSnsTopic.topicArn],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'sagemaker:DescribeTrainingJob',
      ],
      resources: [`arn:${Aws.PARTITION}:sagemaker:${Aws.REGION}:${Aws.ACCOUNT_ID}:training-job/*`],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        's3:GetObject',
        's3:PutObject',
        's3:DeleteObject',
        's3:ListBucket',
      ],
      resources: [
        `${this.s3Bucket.bucketArn}/*`,
        `${this.s3Bucket.bucketArn}`,
        `arn:${Aws.PARTITION}:s3:::*SageMaker*`,
        `arn:${Aws.PARTITION}:s3:::*Sagemaker*`,
        `arn:${Aws.PARTITION}:s3:::*sagemaker*`,
      ],
    }));

    newRole.addToPolicy(new PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'logs:CreateLogGroup',
        'logs:CreateLogStream',
        'logs:PutLogEvents',
      ],
      resources: ['*'],
    }));

    return newRole;
  }

  private createTrainingEventsBridge() {

    const lambdaFunction = new PythonFunction(this.scope, `${this.baseId}-lambda`, {
      entry: `${this.src}/trainings`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_12,
      index: 'training_event.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.iamRole(),
      memorySize: 2048,
      environment: {
        TRAINING_JOB_TABLE: this.trainingTable.tableName,
        CHECKPOINT_TABLE: this.checkpointTable.tableName,
        USER_EMAIL_TOPIC_ARN: this.userSnsTopic.topicArn,
        LOG_LEVEL: this.logLevel.valueAsString,
      },
      layers: [this.layer],
    });

    const rule = new Rule(this.scope, `${this.baseId}-rule`, {
      eventPattern: {
        source: ['aws.sagemaker'],
        detailType: ['SageMaker Training Job State Change'],
      },
    });

    rule.addTarget(new LambdaFunction(lambdaFunction));

  }
}
