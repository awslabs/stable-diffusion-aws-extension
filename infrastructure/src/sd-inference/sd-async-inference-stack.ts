import * as python from '@aws-cdk/aws-lambda-python-alpha';
import { PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha';
import {
  Aws,
  aws_dynamodb,
  aws_ecr,
  aws_sns,
  CfnParameter,
  CustomResource,
  Duration,
  RemovalPolicy,
  StackProps,
} from 'aws-cdk-lib';
import * as apigw from 'aws-cdk-lib/aws-apigateway';

import { Resource } from 'aws-cdk-lib/aws-apigateway/lib/resource';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as iam from 'aws-cdk-lib/aws-iam';
import { PolicyStatementProps } from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as eventSources from 'aws-cdk-lib/aws-lambda-event-sources';
import { RetentionDays } from 'aws-cdk-lib/aws-logs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sns from 'aws-cdk-lib/aws-sns';
import { Size } from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import { CreateInferenceJobApi, CreateInferenceJobApiProps } from '../api/inferences/create-inference-job';
import { DeleteInferenceJobsApi, DeleteInferenceJobsApiProps } from '../api/inferences/delete-inference-jobs';
import { GetInferenceJobApi, GetInferenceJobApiProps } from '../api/inferences/get-inference-job';
import { ListInferencesApi } from '../api/inferences/list-inferences';
import { StartInferenceJobApi, StartInferenceJobApiProps } from '../api/inferences/start-inference-job';
import { DockerImageName, ECRDeployment } from '../cdk-ecr-deployment/lib';
import { AIGC_WEBUI_INFERENCE } from '../common/dockerImages';
import { ResourceProvider } from '../shared/resource-provider';
import { EndpointStack, EndpointStackProps } from '../endpoints/endpoint-stack';

/*
AWS CDK code to create API Gateway, Lambda and SageMaker inference endpoint for txt2img/img2img inference
based on Stable Diffusion. S3 is used to store large payloads and passed as object reference in the API Gateway
request and Lambda function to avoid request payload limitation
Note: Sync Inference is put here for reference, we use Async Inference now
*/
export interface SDAsyncInferenceStackProps extends StackProps {
  inferenceErrorTopic: sns.Topic;
  inferenceResultTopic: sns.Topic;
  routers: { [key: string]: Resource };
  s3_bucket: s3.Bucket;
  training_table: dynamodb.Table;
  multiUserTable: dynamodb.Table;
  snsTopic: aws_sns.Topic;
  ecr_image_tag: string;
  sd_inference_job_table: aws_dynamodb.Table;
  sd_endpoint_deployment_job_table: aws_dynamodb.Table;
  checkpointTable: aws_dynamodb.Table;
  commonLayer: PythonLayerVersion;
  logLevel: CfnParameter;
  resourceProvider: ResourceProvider;
}

export class SDAsyncInferenceStack {

  private resourceProvider: ResourceProvider;

  constructor(
    scope: Construct,
    props: SDAsyncInferenceStackProps,
  ) {
    if (!props?.ecr_image_tag) {
      throw new Error('ecr_image_tag is required');
    }

    this.resourceProvider = props.resourceProvider;

    const srcImg = AIGC_WEBUI_INFERENCE + props?.ecr_image_tag;

    const inferenceECR_url = this.createInferenceECR(scope, srcImg);

    const inference = props.routers.inference;
    const inferV2Router = props.routers.inferences.addResource('{id}');
    const srcRoot = '../middleware_api/lambda';

    const createInferenceJobApi = new CreateInferenceJobApi(
      scope, 'CreateInferenceJob',
            <CreateInferenceJobApiProps>{
              checkpointTable: props.checkpointTable,
              commonLayer: props.commonLayer,
              endpointDeploymentTable: props.sd_endpoint_deployment_job_table,
              httpMethod: 'POST',
              inferenceJobTable: props.sd_inference_job_table,
              router: props.routers.inferences,
              s3Bucket: props.s3_bucket,
              srcRoot: srcRoot,
              multiUserTable: props.multiUserTable,
              logLevel: props.logLevel,
            },
    );

    new StartInferenceJobApi(
      scope, 'StartInferenceJob',
            <StartInferenceJobApiProps>{
              userTable: props.multiUserTable,
              checkpointTable: props.checkpointTable,
              commonLayer: props.commonLayer,
              endpointDeploymentTable: props.sd_endpoint_deployment_job_table,
              httpMethod: 'PUT',
              inferenceJobTable: props.sd_inference_job_table,
              router: inferV2Router,
              s3Bucket: props.s3_bucket,
              srcRoot: srcRoot,
              logLevel: props.logLevel,
            },
    );

    new EndpointStack(
      scope, 'SD',
            <EndpointStackProps>{
              inferenceErrorTopic: props.inferenceErrorTopic,
              inferenceResultTopic: props.inferenceResultTopic,
              routers: props.routers,
              s3Bucket: props?.s3_bucket,
              multiUserTable: props.multiUserTable,
              snsTopic: props?.snsTopic,
              EndpointDeploymentJobTable: props.sd_endpoint_deployment_job_table,
              checkpointTable: props.checkpointTable,
              commonLayer: props.commonLayer,
              logLevel: props.logLevel,
              ecrUrl: inferenceECR_url,
            },
    );

    new ListInferencesApi(
      scope, 'ListInferenceJobs',
      {
        inferenceJobTable: props.sd_inference_job_table,
        commonLayer: props.commonLayer,
        endpointDeploymentTable: props.sd_endpoint_deployment_job_table,
        multiUserTable: props.multiUserTable,
        httpMethod: 'GET',
        router: props.routers.inferences,
        srcRoot: srcRoot,
        logLevel: props.logLevel,
      },
    );

    const inferenceLambdaRole = new iam.Role(scope, 'InferenceLambdaRole', {
      assumedBy: new iam.CompositePrincipal(
        new iam.ServicePrincipal('sagemaker.amazonaws.com'),
        new iam.ServicePrincipal('lambda.amazonaws.com'),
      ),
    });

    inferenceLambdaRole.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
    );

    // Create a Lambda function for inference
    const inferenceLambda = new lambda.DockerImageFunction(
      scope,
      'InferenceLambda',
      {
        code: lambda.DockerImageCode.fromImageAsset(
          '../middleware_api/lambda/inference',
        ),
        timeout: Duration.minutes(15),
        memorySize: 3008,
        environment: {
          INFERENCE_JOB_TABLE: props.sd_inference_job_table.tableName,
          DDB_TRAINING_TABLE_NAME: props?.training_table.tableName ?? '',
          DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME: props.sd_endpoint_deployment_job_table.tableName,
          S3_BUCKET: props?.s3_bucket.bucketName ?? '',
          ACCOUNT_ID: Aws.ACCOUNT_ID,
          REGION_NAME: Aws.REGION,
          SNS_INFERENCE_SUCCESS: props.inferenceResultTopic.topicName,
          SNS_INFERENCE_ERROR: props.inferenceErrorTopic.topicName,
          NOTICE_SNS_TOPIC: props?.snsTopic.topicArn ?? '',
          INFERENCE_ECR_IMAGE_URL: inferenceECR_url,
          LOG_LEVEL: props.logLevel.valueAsString,
        },
        role: inferenceLambdaRole,
        logRetention: RetentionDays.ONE_WEEK,
      },
    );

    // Grant Lambda permission to read/write from/to the S3 bucket
    props?.s3_bucket.grantReadWrite(inferenceLambda);

    // Grant Lambda permission to invoke SageMaker endpoint
    inferenceLambda.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          'sagemaker:DescribeEndpoint',
          'sagemaker:ListEndpoints',
          'sagemaker:DeleteEndpoint',
          'sagemaker:InvokeEndpoint',
          'sagemaker:InvokeEndpointAsync',
          'application-autoscaling:DeregisterScalableTarget',
          's3:CreateBucket',
          's3:ListBucket',
          's3:GetObject',
        ],
        resources: ['*'],
      }),
    );


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
        props.sd_endpoint_deployment_job_table.tableArn,
        props.sd_inference_job_table.tableArn,
      ],
    });
    const s3Statement = new iam.PolicyStatement({
      actions: [
        's3:Get*',
        's3:List*',
        's3:PutObject',
        's3:GetObject',
      ],
      resources: [
        props.s3_bucket.bucketArn,
        `${props.s3_bucket.bucketArn}/*`,
        `arn:${Aws.PARTITION}:s3:::*sagemaker*`,
      ],
    });
    const snsStatement = new iam.PolicyStatement(<PolicyStatementProps>{
      actions: [
        'sns:Publish',
        'sns:ListTopics',
      ],
      resources: [
        props?.snsTopic.topicArn,
        props.inferenceErrorTopic.topicArn,
        props.inferenceResultTopic.topicArn,
      ],
    });
    inferenceLambda.addToRolePolicy(ddbStatement);
    inferenceLambda.addToRolePolicy(s3Statement);
    inferenceLambda.addToRolePolicy(snsStatement);

    // Create a POST method for the API Gateway and connect it to the Lambda function
    const txt2imgIntegration = new apigw.LambdaIntegration(inferenceLambda);

    new GetInferenceJobApi(
      scope, 'GetInferenceJob',
            <GetInferenceJobApiProps>{
              router: inferV2Router,
              commonLayer: props.commonLayer,
              inferenceJobTable: props.sd_inference_job_table,
              userTable: props.multiUserTable,
              httpMethod: 'GET',
              s3Bucket: props.s3_bucket,
              srcRoot: srcRoot,
              logLevel: props.logLevel,
            },
    );

    const deleteInferenceJobsApi= new DeleteInferenceJobsApi(
      scope, 'DeleteInferenceJobs',
            <DeleteInferenceJobsApiProps>{
              router: props.routers.inferences,
              commonLayer: props.commonLayer,
              userTable: props.multiUserTable,
              inferenceJobTable: props.sd_inference_job_table,
              httpMethod: 'DELETE',
              s3Bucket: props.s3_bucket,
              srcRoot: srcRoot,
              logLevel: props.logLevel,
            },
    );
    deleteInferenceJobsApi.model.node.addDependency(createInferenceJobApi.model);
    deleteInferenceJobsApi.requestValidator.node.addDependency(createInferenceJobApi.requestValidator);

    // Add a POST method with prefix inference
    if (!inference) {
      throw new Error('inference is undefined');
    }

    const run_sagemaker_inference = inference.addResource(
      'run-sagemaker-inference',
    );
    run_sagemaker_inference.addMethod('POST', txt2imgIntegration, {
      apiKeyRequired: true,
    });

    const handler = new python.PythonFunction(
      scope,
      'InferenceResultNotification',
      {
        entry: `${srcRoot}/inferences`,
        runtime: lambda.Runtime.PYTHON_3_9,
        handler: 'handler',
        index: 'inference_async_events.py',
        memorySize: 10240,
        ephemeralStorageSize: Size.gibibytes(10),
        timeout: Duration.seconds(900),
        environment: {
          INFERENCE_JOB_TABLE: props.sd_inference_job_table.tableName,
          DDB_TRAINING_TABLE_NAME: props?.training_table.tableName ?? '',
          DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME: props.sd_endpoint_deployment_job_table.tableName,
          S3_BUCKET_NAME: props?.s3_bucket.bucketName ?? '',
          ACCOUNT_ID: Aws.ACCOUNT_ID,
          REGION_NAME: Aws.REGION,
          SNS_INFERENCE_SUCCESS: props.inferenceResultTopic.topicName,
          SNS_INFERENCE_ERROR: props.inferenceErrorTopic.topicName,
          NOTICE_SNS_TOPIC: props?.snsTopic.topicArn ?? '',
          INFERENCE_ECR_IMAGE_URL: inferenceECR_url,
          LOG_LEVEL: props.logLevel.valueAsString,
        },
        layers: [props.commonLayer],
        logRetention: RetentionDays.ONE_WEEK,
      },
    );

    handler.addToRolePolicy(s3Statement);
    handler.addToRolePolicy(ddbStatement);
    handler.addToRolePolicy(snsStatement);

    // Add the SNS topic as an event source for the Lambda function
    handler.addEventSource(
      new eventSources.SnsEventSource(props.inferenceResultTopic),
    );
    handler.addEventSource(
      new eventSources.SnsEventSource(props.inferenceErrorTopic),
    );
  }

  private createInferenceECR(scope: Construct, srcImg: string) {
    const dockerRepo = new aws_ecr.Repository(
      scope,
      'EsdEcrInferenceRepo',
      {
        repositoryName: 'stable-diffusion-aws-extension/aigc-webui-inference',
        removalPolicy: RemovalPolicy.DESTROY,
      },
    );

    const ecrDeployment = new ECRDeployment(
      scope,
      'EsdEcrInferenceDeploy',
      {
        src: new DockerImageName(srcImg),
        dest: new DockerImageName(`${dockerRepo.repositoryUri}:latest`),
        environment: {
          BUCKET_NAME: this.resourceProvider.bucketName,
        },
      },
    );

    // trigger the custom resource lambda
    const customJob = new CustomResource(
      scope,
      'EsdEcrInferenceImage',
      {
        serviceToken: ecrDeployment.serviceToken,
        resourceType: 'Custom::AIGCSolutionECRLambda',
        properties: {
          SrcImage: `docker://${srcImg}`,
          DestImage: `docker://${dockerRepo.repositoryUri}:latest`,
          RepositoryName: `${dockerRepo.repositoryName}`,
        },
      },
    );

    customJob.node.addDependency(ecrDeployment);

    return dockerRepo.repositoryUri;
  }
}
