import { Aws, aws_dynamodb, aws_lambda, CfnParameter, StackProps } from 'aws-cdk-lib';

import { Resource } from 'aws-cdk-lib/aws-apigateway/lib/resource';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';
import { SqsStack } from './comfy-sqs';
import { CreateSageMakerEndpoint, CreateSageMakerEndpointProps } from '../api/comfy/create_endpoint';
import { ExecuteApi, ExecuteApiProps } from '../api/comfy/excute';
import { GetPrepareApi, GetPrepareApiProps } from '../api/comfy/get_prepare';
import { GetExecuteApi, GetExecuteApiProps } from '../api/comfy/get_execute';
import { GetSyncMsgApi, GetSyncMsgApiProps } from '../api/comfy/get_sync_msg';
import { PrepareApi, PrepareApiProps } from '../api/comfy/prepare';
import { SyncMsgApi, SyncMsgApiProps } from '../api/comfy/sync_msg';
import { ResourceProvider } from '../shared/resource-provider';
import { ICfnRuleConditionExpression } from 'aws-cdk-lib/core/lib/cfn-condition';
import { QueryExecuteApi, QueryExecuteApiProps } from '../api/comfy/query_execute';

export interface ComfyInferenceStackProps extends StackProps {
  routers: { [key: string]: Resource };
  s3Bucket: s3.Bucket;
  ecrImageTag: string;
  configTable: aws_dynamodb.Table;
  executeTable: aws_dynamodb.Table;
  modelTable: aws_dynamodb.Table;
  syncTable: aws_dynamodb.Table;
  msgTable:aws_dynamodb.Table;
  commonLayer: aws_lambda.LayerVersion;
  ecrRepositoryName: string;
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

    // new EndpointStack(
    //   scope, 'Comfy', <EndpointStackProps>{
    //     inferenceErrorTopic: props.inferenceErrorTopic,
    //     inferenceResultTopic: props.inferenceResultTopic,
    //     routers: props.routers,
    //     s3Bucket: props.s3Bucket,
    //     multiUserTable: props.multiUserTable,
    //     snsTopic: props?.snsTopic,
    //     EndpointDeploymentJobTable: props.endpointTable,
    //     commonLayer: props.commonLayer,
    //     logLevel: props.logLevel,
    //     accountId: props.accountId,
    //     ecrImageTag: props.ecrImageTag,
    //   },
    // );

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
