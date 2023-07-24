import { PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha';
import {
  aws_apigateway,
  aws_dynamodb,
  aws_dynamodb as dynamodb,
  aws_s3,
  aws_sns,
  aws_sns_subscriptions as sns_subscriptions,
  CfnParameter,
  NestedStack,
  RemovalPolicy,
  StackProps,
} from 'aws-cdk-lib';
import { AttributeType } from 'aws-cdk-lib/aws-dynamodb';
import { Runtime } from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import { BlockPublicAccess } from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';
import { CreateCheckPointApi } from './chekpoint-create-api';
import { UpdateCheckPointApi } from './chekpoint-update-api';
import { ListAllCheckPointsApi } from './chekpoints-listall-api';
import { CreateDatasetApi } from './dataset-create-api';
import { UpdateDatasetApi } from './dataset-update-api';
import { ListAllDatasetItemsApi } from './datasets-item-listall-api';
import { ListAllDatasetsApi } from './datasets-listall-api';
import { CreateModelJobApi } from './model-job-create-api';
import { ListAllModelJobApi } from './model-job-listall-api';
import { UpdateModelStatusRestApi } from './model-update-status-api';
import { RestApiGateway } from './rest-api-gateway';

import { CreateTrainJobApi } from './train-job-create-api';
import { ListAllTrainJobsApi } from './train-job-listall-api';
import { UpdateTrainJobApi } from './train-job-update-api';

// ckpt -> create_model -> model -> training -> ckpt -> inference
export interface SdTrainDeployStackProps extends StackProps {
  emailParam: CfnParameter;
  apiKey: string;
  modelInfInstancetype: string;
  ecr_image_tag: string;
}

export class SdTrainDeployStack extends NestedStack {

  public readonly s3Bucket: aws_s3.Bucket;
  public readonly trainingTable: aws_dynamodb.Table;
  public readonly modelTable: aws_dynamodb.Table;
  public readonly checkPointTable: aws_dynamodb.Table;
  public readonly datasetInfoTable: aws_dynamodb.Table;
  public readonly datasetItemTable: aws_dynamodb.Table;
  public apiGateway: aws_apigateway.RestApi;
  public readonly snsTopic: aws_sns.Topic;
  public readonly default_endpoint_name: string;

  private readonly srcRoot='../middleware_api/lambda';
  // private readonly parentScope: Construct;

  constructor(scope: Construct, id: string, props?: SdTrainDeployStackProps) {
    super(scope, id, props);
    // this.parentScope = scope;

    // Check that props.emailParam and props.bucketName are not undefined
    if (!props || props.emailParam === undefined ) {
      throw new Error('emailParam and bucketName must be provided');
    }
    // Use the parameters passed from Middleware
    this.snsTopic = this.createSns(props.emailParam);
    this.s3Bucket = this.createS3Bucket();
    // Upload api template file to the S3 bucket
    new s3deploy.BucketDeployment(this, 'DeployApiTemplate', {
      sources: [s3deploy.Source.asset(`${this.srcRoot}/common/template`)],
      destinationBucket: this.s3Bucket,
      destinationKeyPrefix: 'template',
    });

    const commonLayer = this.commonLayer();
    this.default_endpoint_name = '';

    // Create DynamoDB table to store model job id
    this.modelTable = new dynamodb.Table(this, 'ModelTable', {
      tableName: 'ModelTable',
      partitionKey: { name: 'id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    // Create DynamoDB table to store training job id
    this.trainingTable = new dynamodb.Table(this, 'TrainingTable', {
      tableName: 'TrainingTable',
      partitionKey: { name: 'id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    this.checkPointTable = new dynamodb.Table(this, 'CheckpointTable', {
      tableName: 'CheckpointTable',
      partitionKey: {
        name: 'id',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    this.datasetInfoTable = new dynamodb.Table(this, 'DatasetInfoTable', {
      tableName: 'DatasetInfoTable',
      partitionKey: {
        name: 'dataset_name',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    this.datasetItemTable = new dynamodb.Table(this, 'DatasetItemTable', {
      tableName: 'DatasetItemTable',
      partitionKey: {
        name: 'dataset_name',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'sort_key',
        type: AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    // api gateway setup
    const restApi = new RestApiGateway(this, props.apiKey, [
      'model',
      'models',
      'checkpoint',
      'checkpoints',
      'train',
      'trains',
      'dataset',
      'datasets',
    ]);
    this.apiGateway = restApi.apiGateway;
    const routers = restApi.routers;

    // GET /trains
    new ListAllTrainJobsApi(this, 'aigc-trains', {
      commonLayer: commonLayer,
      httpMethod: 'GET',
      router: routers.trains,
      s3Bucket: this.s3Bucket,
      srcRoot: this.srcRoot,
      trainTable: this.trainingTable,
    });

    // POST /train
    new CreateTrainJobApi(this, 'aigc-create-train', {
      checkpointTable: this.checkPointTable,
      commonLayer: commonLayer,
      httpMethod: 'POST',
      modelTable: this.modelTable,
      router: routers.train,
      s3Bucket: this.s3Bucket,
      srcRoot: this.srcRoot,
      trainTable: this.trainingTable,
    });

    // PUT /train
    new UpdateTrainJobApi(this, 'aigc-put-train', {
      checkpointTable: this.checkPointTable,
      commonLayer: commonLayer,
      httpMethod: 'PUT',
      modelTable: this.modelTable,
      router: routers.train,
      s3Bucket: this.s3Bucket,
      srcRoot: this.srcRoot,
      trainTable: this.trainingTable,
      userTopic: this.snsTopic,
      ecr_image_tag: props.ecr_image_tag,
    });

    // POST /model
    new CreateModelJobApi(this, 'aigc-create-model', {
      router: routers.model,
      s3Bucket: this.s3Bucket,
      srcRoot: this.srcRoot,
      modelTable: this.modelTable,
      commonLayer: commonLayer,
      httpMethod: 'POST',
      checkpointTable: this.checkPointTable,
    });

    // GET /models
    new ListAllModelJobApi(this, 'aigc-listall-model', {
      router: routers.models,
      srcRoot: this.srcRoot,
      modelTable: this.modelTable,
      commonLayer: commonLayer,
      httpMethod: 'GET',
    });

    // PUT /model
    const modelStatusRestApi = new UpdateModelStatusRestApi(this, 'aigc-update-model', {
      s3Bucket: this.s3Bucket,
      router: routers.model,
      httpMethod: 'PUT',
      commonLayer: commonLayer,
      srcRoot: this.srcRoot,
      modelTable: this.modelTable,
      snsTopic: this.snsTopic,
      checkpointTable: this.checkPointTable,
      trainMachineType: props.modelInfInstancetype,
      ecr_image_tag: props.ecr_image_tag,
    });

    this.default_endpoint_name = modelStatusRestApi.sagemakerEndpoint.modelEndpoint.attrEndpointName;

    // GET /checkpoints
    new ListAllCheckPointsApi(this, 'aigc-list-all-ckpts', {
      s3Bucket: this.s3Bucket,
      checkpointTable: this.checkPointTable,
      commonLayer: commonLayer,
      httpMethod: 'GET',
      router: routers.checkpoints,
      srcRoot: this.srcRoot,
    });

    // POST /checkpoint
    new CreateCheckPointApi(this, 'aigc-create-ckpt', {
      checkpointTable: this.checkPointTable,
      commonLayer: commonLayer,
      httpMethod: 'POST',
      router: routers.checkpoint,
      s3Bucket: this.s3Bucket,
      srcRoot: this.srcRoot,
    });

    // PUT /checkpoint
    new UpdateCheckPointApi(this, 'aigc-update-ckpt', {
      checkpointTable: this.checkPointTable,
      commonLayer: commonLayer,
      httpMethod: 'PUT',
      router: routers.checkpoint,
      s3Bucket: this.s3Bucket,
      srcRoot: this.srcRoot,
    });

    // POST /dataset
    new CreateDatasetApi(this, 'aigc-create-dataset', {
      commonLayer: commonLayer,
      datasetInfoTable: this.datasetInfoTable,
      datasetItemTable: this.datasetItemTable,
      httpMethod: 'POST',
      router: routers.dataset,
      s3Bucket: this.s3Bucket,
      srcRoot: this.srcRoot,
    });

    // PUT /dataset
    new UpdateDatasetApi(this, 'aigc-update-dataset', {
      commonLayer: commonLayer,
      datasetInfoTable: this.datasetInfoTable,
      datasetItemTable: this.datasetItemTable,
      httpMethod: 'PUT',
      router: routers.dataset,
      s3Bucket: this.s3Bucket,
      srcRoot: this.srcRoot,
    });

    // GET /datasets
    new ListAllDatasetsApi(this, 'aigc-listall-datasets', {
      commonLayer: commonLayer,
      datasetInfoTable: this.datasetInfoTable,
      httpMethod: 'GET',
      router: routers.datasets,
      s3Bucket: this.s3Bucket,
      srcRoot: this.srcRoot,
    });

    // GET /dataset/{dataset_name}/data
    new ListAllDatasetItemsApi(this, 'aigc-listall-dataset-items', {
      commonLayer: commonLayer,
      datasetInfoTable: this.datasetInfoTable,
      datasetItemsTable: this.datasetItemTable,
      httpMethod: 'GET',
      router: routers.dataset,
      s3Bucket: this.s3Bucket,
      srcRoot: this.srcRoot,
    });
  }

  private createSns(emailParam: CfnParameter): aws_sns.Topic {
    // CDK parameters for SNS email address
    // Create SNS topic for notifications
    // const snsKmsKey = new kms.Key(this, 'SNSTrainEncryptionKey');
    // const snsKey = new kms.Key(this, "KmsMasterKey", {
    //   enableKeyRotation: true,
    //   policy: new iam.PolicyDocument({
    //     assignSids: true,
    //     statements: [
    //       new iam.PolicyStatement({
    //         actions: ["kms:GenerateDataKey*", "kms:Decrypt", "kms:Encrypt"],
    //         resources: ["*"],
    //         effect: iam.Effect.ALLOW,
    //         principals: [
    //           new iam.ServicePrincipal("sns.amazonaws.com"),
    //           new iam.ServicePrincipal("cloudwatch.amazonaws.com"),
    //           new iam.ServicePrincipal("events.amazonaws.com"),
    //           new iam.ServicePrincipal('sagemaker.amazonaws.com'),
    //         ],
    //       }),
    //       new iam.PolicyStatement({
    //         actions: [
    //           "kms:Create*",
    //           "kms:Describe*",
    //           "kms:Enable*",
    //           "kms:List*",
    //           "kms:Put*",
    //           "kms:Update*",
    //           "kms:Revoke*",
    //           "kms:Disable*",
    //           "kms:Get*",
    //           "kms:Delete*",
    //           "kms:ScheduleKeyDeletion",
    //           "kms:CancelKeyDeletion",
    //           "kms:GenerateDataKey",
    //           "kms:TagResource",
    //           "kms:UntagResource",
    //         ],
    //         resources: ["*"],
    //         effect: iam.Effect.ALLOW,
    //         principals: [new iam.AccountRootPrincipal()],
    //       }),
    //     ],
    //   }),
    // });
    
    const snsTopic = new aws_sns.Topic(this, 'StableDiffusionSnsTopic', {
      // masterKey: snsKey,
    });

    // Subscribe user to SNS notifications
    snsTopic.addSubscription(
      new sns_subscriptions.EmailSubscription(emailParam.valueAsString),
    );

    return snsTopic;
  }

  private createS3Bucket(): s3.Bucket {

    // Define the CORS configuration
    const corsRules: s3.CorsRule[] = [
      {
        allowedHeaders: ['*'],
        allowedMethods: [s3.HttpMethods.PUT, s3.HttpMethods.HEAD, s3.HttpMethods.GET],
        allowedOrigins: ['*'],
      },
    ];

    //The code that defines your stack goes here
    return new s3.Bucket(this, 'aigc-bucket', {
      blockPublicAccess: BlockPublicAccess.BLOCK_ACLS,
      removalPolicy: RemovalPolicy.RETAIN,
      cors: corsRules,
    });
  }

  private commonLayer() {
    return new PythonLayerVersion(this, 'aigc-common-layer', {
      entry: `${this.srcRoot}`,
      bundling: {
        outputPathSuffix: '/python',
      },
      compatibleRuntimes: [Runtime.PYTHON_3_9],
    });
  }
}
