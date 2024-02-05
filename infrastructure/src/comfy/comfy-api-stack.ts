import { Aws, aws_dynamodb, aws_lambda, CfnParameter, StackProps } from 'aws-cdk-lib';

import { Resource } from 'aws-cdk-lib/aws-apigateway/lib/resource';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';
import { ExecuteApi, ExecuteApiProps } from '../api/comfy/excute';
import { CreateSageMakerEndpoint, CreateSageMakerEndpointProps } from '../api/comfy/create_endpoint';
import { GetExecuteApi, GetExecuteApiProps } from '../api/comfy/get_prompt';
import { GetSyncMsgApi, GetSyncMsgApiProps } from '../api/comfy/get_sync_msg';
import { SyncMsgApi, SyncMsgApiProps } from '../api/comfy/sync_msg';
import { ResourceProvider } from '../shared/resource-provider';
import { SqsStack } from './comfy-sqs';

export interface ComfyInferenceStackProps extends StackProps {
  routers: { [key: string]: Resource };
  s3Bucket: s3.Bucket;
  ecrImageTag: string;
  configTable: aws_dynamodb.Table;
  executeTable: aws_dynamodb.Table;
  endpointTable: aws_dynamodb.Table;
  modelTable: aws_dynamodb.Table;
  nodeTable: aws_dynamodb.Table;
  msgTable:aws_dynamodb.Table;
  commonLayer: aws_lambda.LayerVersion;
  ecrRepositoryName: string;
  logLevel: CfnParameter;
  resourceProvider: ResourceProvider;
}

export class ComfyApiStack extends Construct {
  private resourceProvider: ResourceProvider;
  private readonly layer: aws_lambda.LayerVersion;
  private configTable: aws_dynamodb.Table;
  private executeTable: aws_dynamodb.Table;
  private endpointTable: aws_dynamodb.Table;
  private modelTable: aws_dynamodb.Table;
  private nodeTable: aws_dynamodb.Table;
  private msgTable: aws_dynamodb.Table;


  constructor(scope: Construct, id: string, props: ComfyInferenceStackProps) {
    super(scope, id);
    if (!props?.ecrImageTag) {
      throw new Error('ecrImageTag is required');
    }
    this.layer = props.commonLayer;
    this.resourceProvider = props.resourceProvider;
    this.configTable = props.configTable;
    this.executeTable = props.executeTable;
    this.endpointTable = props.endpointTable;
    this.modelTable = props.modelTable;
    this.nodeTable = props.nodeTable;
    this.msgTable = props.msgTable;

    const srcImg = Aws.ACCOUNT_ID + '.dkr.ecr.' + Aws.REGION + '.amazonaws.com/comfyui-aws-extension/gen-ai-comfyui-inference:' + props?.ecrImageTag;
    const srcRoot = '../middleware_api/lambda';

    const model_data_url = 's3://' + props.s3Bucket.bucketName + '/data/model.tar.gz';

    const syncMsgGetRouter = props.routers.sync.addResource('{id}');

    const executeGetRouter = props.routers.execute.addResource('{id}');

    const inferenceLambdaRole = new iam.Role(scope, 'InferenceLambdaRole', {
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

    new CreateSageMakerEndpoint(scope, 'ComfyEndpoint',
            <CreateSageMakerEndpointProps>{
              dockerImageUrl: srcImg,
              modelDataUrl: model_data_url,
              s3Bucket: props.s3Bucket,
              machineType: 'ml.g5.xlarge',
              rootSrc: srcRoot,
              endpointTable: this.endpointTable,
              configTable: this.endpointTable,
              modelTable: this.endpointTable,
              nodeTable: this.endpointTable,
              commonLayer: this.layer,
              queue: sqsStack.queue,
              resourceProvider: this.resourceProvider,
              logLevel: props.logLevel,
            });

    // POST /execute
    new ExecuteApi(
      scope, 'Execute',
            <ExecuteApiProps>{
              httpMethod: 'POST',
              router: props.routers.execute,
              srcRoot: srcRoot,
              s3Bucket: props.s3Bucket,
              configTable: this.configTable,
              executeTable: this.executeTable,
              endpointTable: this.endpointTable,
              modelTable: this.modelTable,
              nodeTable: this.nodeTable,
              queue: sqsStack.queue,
              commonLayer: this.layer,
              logLevel: props.logLevel,
            },
    );

    // GET /execute/{id}
    new GetExecuteApi(
      scope, 'GetExecute',
            <GetExecuteApiProps>{
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
  }
}
