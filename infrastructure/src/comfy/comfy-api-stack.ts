import { PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha';
import * as python from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, aws_dynamodb, aws_lambda, aws_sns, aws_sqs, Duration, StackProps } from 'aws-cdk-lib';

import { Resource } from 'aws-cdk-lib/aws-apigateway/lib/resource';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as eventSources from 'aws-cdk-lib/aws-lambda-event-sources';
import { RetentionDays } from 'aws-cdk-lib/aws-logs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import { Size } from 'aws-cdk-lib/core';
import { ICfnRuleConditionExpression } from 'aws-cdk-lib/core/lib/cfn-condition';
import { Construct } from 'constructs';
import { ExecuteApi, ExecuteApiProps } from '../api/comfy/excute';
import { GetExecuteApi, GetExecuteApiProps } from '../api/comfy/get_execute';
import { GetPrepareApi, GetPrepareApiProps } from '../api/comfy/get_prepare';
import { GetSyncMsgApi, GetSyncMsgApiProps } from '../api/comfy/get_sync_msg';
import { PrepareApi, PrepareApiProps } from '../api/comfy/prepare';
import { QueryExecuteApi, QueryExecuteApiProps } from '../api/comfy/query_execute';
import { SyncMsgApi, SyncMsgApiProps } from '../api/comfy/sync_msg';
import { ResourceProvider } from '../shared/resource-provider';

export interface ComfyInferenceStackProps extends StackProps {
  routers: { [key: string]: Resource };
  s3Bucket: s3.Bucket;
  configTable: aws_dynamodb.Table;
  executeTable: aws_dynamodb.Table;
  syncTable: aws_dynamodb.Table;
  msgTable:aws_dynamodb.Table;
  multiUserTable: aws_dynamodb.Table;
  endpointTable: aws_dynamodb.Table;
  instanceMonitorTable: aws_dynamodb.Table;
  commonLayer: PythonLayerVersion;
  ecrRepositoryName: string;
  executeSuccessTopic: sns.Topic;
  executeFailTopic: sns.Topic;
  snsTopic: aws_sns.Topic;
  resourceProvider: ResourceProvider;
  accountId: ICfnRuleConditionExpression;
  queue: sqs.Queue;
}

export class ComfyApiStack extends Construct {
  private readonly layer: aws_lambda.LayerVersion;
  private readonly configTable: aws_dynamodb.Table;
  private readonly executeTable: aws_dynamodb.Table;
  private readonly syncTable: aws_dynamodb.Table;
  private readonly msgTable: aws_dynamodb.Table;
  private readonly instanceMonitorTable: aws_dynamodb.Table;
  private readonly endpointTable: aws_dynamodb.Table;
  private readonly queue: aws_sqs.Queue;


  constructor(scope: Construct, id: string, props: ComfyInferenceStackProps) {
    super(scope, id);
    this.layer = props.commonLayer;
    this.configTable = props.configTable;
    this.executeTable = props.executeTable;
    this.syncTable = props.syncTable;
    this.msgTable = props.msgTable;
    this.instanceMonitorTable = props.instanceMonitorTable;
    this.endpointTable = props.endpointTable;
    this.queue = props.queue;

    const srcRoot = '../middleware_api/lambda';

    const syncMsgGetRouter = props.routers.sync.addResource('{id}');

    const executeGetRouter = props.routers.executes.addResource('{id}');

    const prepareGetRouter = props.routers.prepare.addResource('{id}');

    const inferenceLambdaRole = new iam.Role(scope, 'ComfyInferenceLambdaRole', {
      assumedBy: new iam.CompositePrincipal(
        new iam.ServicePrincipal('sagemaker.amazonaws.com'),
        new iam.ServicePrincipal('lambda.amazonaws.com'),
      ),
    });

    inferenceLambdaRole.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
    );

    new GetSyncMsgApi(scope, 'GetSyncMsg', <GetSyncMsgApiProps>{
      httpMethod: 'GET',
      router: syncMsgGetRouter,
      srcRoot: srcRoot,
      s3Bucket: props.s3Bucket,
      configTable: this.configTable,
      msgTable: this.msgTable,
      queue: this.queue,
      commonLayer: this.layer,
    });

    const synMsgApi = new SyncMsgApi(scope, 'SyncMsg', <SyncMsgApiProps>{
      httpMethod: 'POST',
      router: props.routers.sync,
      srcRoot: srcRoot,
      s3Bucket: props.s3Bucket,
      configTable: this.configTable,
      msgTable: this.msgTable,
      queue: this.queue,
      commonLayer: this.layer,
    });

    // POST /executes
    const executeAPi = new ExecuteApi(
      scope, 'Execute', <ExecuteApiProps>{
        httpMethod: 'POST',
        router: props.routers.executes,
        srcRoot: srcRoot,
        configTable: this.configTable,
        executeTable: this.executeTable,
        endpointTable: this.endpointTable,
        commonLayer: this.layer,
      },
    );
    executeAPi.model.node.addDependency(synMsgApi.model);
    executeAPi.requestValidator.node.addDependency(synMsgApi.requestValidator);

    // GET /executes
    new QueryExecuteApi(
      scope, 'QueryExecute', <QueryExecuteApiProps>{
        httpMethod: 'GET',
        router: props.routers.executes,
        srcRoot: srcRoot,
        s3Bucket: props.s3Bucket,
        configTable: this.configTable,
        executeTable: this.executeTable,
        queue: this.queue,
        commonLayer: this.layer,
      },
    );

    // POST /prepare
    const prepareApi = new PrepareApi(
      scope, 'Prepare', <PrepareApiProps>{
        httpMethod: 'POST',
        router: props.routers.prepare,
        srcRoot: srcRoot,
        s3Bucket: props.s3Bucket,
        configTable: this.configTable,
        syncTable: this.syncTable,
        instanceMonitorTable: this.instanceMonitorTable,
        endpointTable: this.endpointTable,
        queue: this.queue,
        commonLayer: this.layer,
      },
    );
    prepareApi.model.node.addDependency(synMsgApi.model);
    prepareApi.requestValidator.node.addDependency(synMsgApi.requestValidator);

    // GET /executes/{id}
    new GetExecuteApi(
      scope, 'GetExecute', <GetExecuteApiProps>{
        httpMethod: 'GET',
        router: executeGetRouter,
        srcRoot: srcRoot,
        s3Bucket: props.s3Bucket,
        configTable: this.configTable,
        executeTable: this.executeTable,
        commonLayer: this.layer,
      },
    );

    // GET /execute/{id}
    new GetPrepareApi(
      scope, 'GetPrepare', <GetPrepareApiProps>{
        httpMethod: 'GET',
        router: prepareGetRouter,
        srcRoot: srcRoot,
        s3Bucket: props.s3Bucket,
        configTable: this.configTable,
        syncTable: this.syncTable,
        instanceMonitorTable: this.instanceMonitorTable,
        commonLayer: this.layer,
      },
    );

    const handler = new python.PythonFunction(scope, 'ComfyInferenceResultNotification', {
      entry: `${srcRoot}/comfy`,
      runtime: lambda.Runtime.PYTHON_3_10,
      handler: 'handler',
      index: 'execute_async_events.py',
      memorySize: 3070,
      tracing: aws_lambda.Tracing.ACTIVE,
      ephemeralStorageSize: Size.gibibytes(10),
      timeout: Duration.seconds(900),
      environment: {
        INFERENCE_JOB_TABLE: props.executeTable.tableName,
        NOTICE_SNS_TOPIC: props.snsTopic.topicArn ?? '',
      },
      layers: [props.commonLayer],
      logRetention: RetentionDays.ONE_WEEK,
    },
    );

    const s3Statement = new iam.PolicyStatement({
      actions: [
        's3:Get*',
        's3:List*',
        's3:PutObject',
        's3:GetObject',
      ],
      resources: [
        props.s3Bucket.bucketArn,
        `${props.s3Bucket.bucketArn}/*`,
        `arn:${Aws.PARTITION}:s3:::*sagemaker*`,
      ],
    });

    const snsStatement = new iam.PolicyStatement({
      actions: [
        'sns:Publish',
        'sns:ListTopics',
      ],
      resources: [
        props?.snsTopic.topicArn,
        props.executeSuccessTopic.topicArn,
        props.executeFailTopic.topicArn,
      ],
    });
    const ddbStatement = new iam.PolicyStatement({
      actions: [
        'dynamodb:Query',
        'dynamodb:GetItem',
        'dynamodb:PutItem',
        'dynamodb:DeleteItem',
        'dynamodb:UpdateItem',
        'dynamodb:Describe*',
        'dynamodb:List*',
        'dynamodb:Scan',
      ],
      resources: [
        props.endpointTable.tableArn,
        props.executeTable.tableArn,
        props.syncTable.tableArn,
        props.configTable.tableArn,
        props.multiUserTable.tableArn,
      ],
    });

    handler.addToRolePolicy(s3Statement);
    handler.addToRolePolicy(ddbStatement);
    handler.addToRolePolicy(snsStatement);

    // Add the SNS topic as an event source for the Lambda function
    handler.addEventSource(
      new eventSources.SnsEventSource(props.executeSuccessTopic),
    );

    handler.addEventSource(
      new eventSources.SnsEventSource(props.executeFailTopic),
    );
  }
}
