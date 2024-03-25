import { PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, aws_dynamodb, aws_lambda, aws_sns, CfnParameter, StackProps } from 'aws-cdk-lib';

import { Resource } from 'aws-cdk-lib/aws-apigateway/lib/resource';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sns from 'aws-cdk-lib/aws-sns';
import { ICfnRuleConditionExpression } from 'aws-cdk-lib/core/lib/cfn-condition';
import { Construct } from 'constructs';
import { SqsStack } from './comfy-sqs';
import { CreateSageMakerEndpoint, CreateSageMakerEndpointProps } from '../api/comfy/create_endpoint';
import { ExecuteApi, ExecuteApiProps } from '../api/comfy/excute';
import { GetExecuteApi, GetExecuteApiProps } from '../api/comfy/get_execute';
import { GetPrepareApi, GetPrepareApiProps } from '../api/comfy/get_prepare';
import { GetSyncMsgApi, GetSyncMsgApiProps } from '../api/comfy/get_sync_msg';
import { PrepareApi, PrepareApiProps } from '../api/comfy/prepare';
import { QueryExecuteApi, QueryExecuteApiProps } from '../api/comfy/query_execute';
import { SyncMsgApi, SyncMsgApiProps } from '../api/comfy/sync_msg';
import { EndpointStack, EndpointStackProps } from '../endpoints/endpoint-stack';
import { ResourceProvider } from '../shared/resource-provider';

export interface ComfyInferenceStackProps extends StackProps {
  routers: { [key: string]: Resource };
  s3Bucket: s3.Bucket;
  ecrImageTag: CfnParameter;
  configTable: aws_dynamodb.Table;
  executeTable: aws_dynamodb.Table;
  modelTable: aws_dynamodb.Table;
  syncTable: aws_dynamodb.Table;
  msgTable:aws_dynamodb.Table;
  multiUserTable: aws_dynamodb.Table;
  endpointTable: aws_dynamodb.Table;
  commonLayer: PythonLayerVersion;
  ecrRepositoryName: string;
  executeSuccessTopic: sns.Topic;
  executeFailTopic: sns.Topic;
  snsTopic: aws_sns.Topic;
  logLevel: CfnParameter;
  resourceProvider: ResourceProvider;
  accountId: ICfnRuleConditionExpression;
}

export class ComfyApiStack extends Construct {
  private readonly layer: aws_lambda.LayerVersion;
  private configTable: aws_dynamodb.Table;
  private executeTable: aws_dynamodb.Table;
  private modelTable: aws_dynamodb.Table;
  private syncTable: aws_dynamodb.Table;
  private msgTable: aws_dynamodb.Table;
  private multiUserTable: aws_dynamodb.Table;
  private endpointTable: aws_dynamodb.Table;
  private executeSuccessTopic: sns.Topic;
  private executeFailTopic: sns.Topic;
  private snsTopic: aws_sns.Topic;


  constructor(scope: Construct, id: string, props: ComfyInferenceStackProps) {
    super(scope, id);
    if (!props?.ecrImageTag) {
      throw new Error('ecrImageTag is required');
    }
    this.layer = props.commonLayer;
    this.configTable = props.configTable;
    this.executeTable = props.executeTable;
    this.modelTable = props.modelTable;
    this.syncTable = props.syncTable;
    this.msgTable = props.msgTable;
    this.executeSuccessTopic = props.executeSuccessTopic;
    this.executeFailTopic = props.executeFailTopic;
    this.snsTopic = props.snsTopic;
    this.multiUserTable = props.multiUserTable;
    this.endpointTable = props.endpointTable;

    const srcImg = Aws.ACCOUNT_ID + '.dkr.ecr.' + Aws.REGION + '.amazonaws.com/comfyui-aws-extension/gen-ai-comfyui-inference:' + props?.ecrImageTag;
    const srcRoot = '../middleware_api/lambda';

    const model_data_url = 's3://' + props.s3Bucket.bucketName + '/data/model.tar.gz';

    const syncMsgGetRouter = props.routers.sync.addResource('{id}');

    const executeGetRouter = props.routers.execute.addResource('{id}');

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

    const sqsStack = new SqsStack(this, 'comfy-sqs', {
      name: 'SyncComfyMsgJob',
      visibilityTimeout: 900,
    });

    new SyncMsgApi(scope, 'SyncMsg', <SyncMsgApiProps>{
      httpMethod: 'POST',
      router: props.routers.sync,
      srcRoot: srcRoot,
      s3Bucket: props.s3Bucket,
      configTable: this.configTable,
      msgTable: this.msgTable,
      queue: sqsStack.queue,
      commonLayer: this.layer,
      logLevel: props.logLevel,
    });

    new GetSyncMsgApi(scope, 'GetSyncMsg', <GetSyncMsgApiProps>{
      httpMethod: 'GET',
      router: syncMsgGetRouter,
      srcRoot: srcRoot,
      s3Bucket: props.s3Bucket,
      configTable: this.configTable,
      msgTable: this.msgTable,
      queue: sqsStack.queue,
      commonLayer: this.layer,
      logLevel: props.logLevel,
    });

    new CreateSageMakerEndpoint(scope, 'ComfyEndpoint', <CreateSageMakerEndpointProps>{
      dockerImageUrl: srcImg,
      modelDataUrl: model_data_url,
      s3Bucket: props.s3Bucket,
      machineType: 'ml.g4dn.2xlarge',
      rootSrc: srcRoot,
      configTable: this.configTable,
      modelTable: this.modelTable,
      syncTable: this.syncTable,
      commonLayer: this.layer,
      queue: sqsStack.queue,
      logLevel: props.logLevel,
    });

    new EndpointStack(
      scope, 'Comfy', <EndpointStackProps>{
        inferenceErrorTopic: this.executeFailTopic,
        inferenceResultTopic: this.executeSuccessTopic,
        routers: props.routers,
        s3Bucket: props.s3Bucket,
        multiUserTable: this.multiUserTable,
        snsTopic: this.snsTopic,
        EndpointDeploymentJobTable: this.endpointTable,
        commonLayer: props.commonLayer,
        logLevel: props.logLevel,
        accountId: props.accountId,
        ecrImageTag: props.ecrImageTag,
      },
    );

    // POST /execute
    new ExecuteApi(
      scope, 'Execute', <ExecuteApiProps>{
        httpMethod: 'POST',
        router: props.routers.execute,
        srcRoot: srcRoot,
        s3Bucket: props.s3Bucket,
        configTable: this.configTable,
        executeTable: this.executeTable,
        queue: sqsStack.queue,
        commonLayer: this.layer,
        logLevel: props.logLevel,
      },
    );

    // POST /execute
    new QueryExecuteApi(
      scope, 'QueryExecute', <QueryExecuteApiProps>{
        httpMethod: 'POST',
        router: props.routers.queryExecute,
        srcRoot: srcRoot,
        s3Bucket: props.s3Bucket,
        configTable: this.configTable,
        executeTable: this.executeTable,
        queue: sqsStack.queue,
        commonLayer: this.layer,
        logLevel: props.logLevel,
      },
    );

    // POST /prepare
    new PrepareApi(
      scope, 'Prepare', <PrepareApiProps>{
        httpMethod: 'POST',
        router: props.routers.prepare,
        srcRoot: srcRoot,
        s3Bucket: props.s3Bucket,
        configTable: this.configTable,
        syncTable: this.syncTable,
        modelTable: this.modelTable,
        queue: sqsStack.queue,
        commonLayer: this.layer,
        logLevel: props.logLevel,
      },
    );

    // GET /execute/{id}
    new GetExecuteApi(
      scope, 'GetExecute', <GetExecuteApiProps>{
        httpMethod: 'GET',
        router: executeGetRouter,
        srcRoot: srcRoot,
        s3Bucket: props.s3Bucket,
        configTable: this.configTable,
        executeTable: this.executeTable,
        commonLayer: this.layer,
        logLevel: props.logLevel,
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
        commonLayer: this.layer,
        logLevel: props.logLevel,
      },
    );
  }
}
