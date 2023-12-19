import * as path from 'path';
import * as python from '@aws-cdk/aws-lambda-python-alpha';
import { PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha';
import {
  StackProps,
  Duration,
  Aws,
  RemovalPolicy,
  aws_ecr,
  CustomResource,
  NestedStack, aws_dynamodb, aws_sns, aws_apigateway,
} from 'aws-cdk-lib';
import * as apigw from 'aws-cdk-lib/aws-apigateway';

import { MethodOptions } from 'aws-cdk-lib/aws-apigateway/lib/method';
import { Resource } from 'aws-cdk-lib/aws-apigateway/lib/resource';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as iam from 'aws-cdk-lib/aws-iam';
import { PolicyStatementProps } from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as eventSources from 'aws-cdk-lib/aws-lambda-event-sources';
import { RetentionDays } from 'aws-cdk-lib/aws-logs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import * as sns from 'aws-cdk-lib/aws-sns';
import { Construct } from 'constructs';
import { InferenceL2Api, InferenceL2ApiProps } from './inference-api-l2';
import { CreateInferenceJobApi, CreateInferenceJobApiProps } from './inference-job-create-api';
import { RunInferenceJobApi, RunInferenceJobApiProps } from './inference-job-run-api';
import { CreateSagemakerEndpointsApi, CreateSagemakerEndpointsApiProps } from './sagemaker-endpoints-create';
import { DeleteSagemakerEndpointsApi, DeleteSagemakerEndpointsApiProps } from './sagemaker-endpoints-delete';
import { SagemakerEndpointEvents, SagemakerEndpointEventsProps } from './sagemaker-endpoints-event';
import { ListAllSagemakerEndpointsApi, ListAllSageMakerEndpointsApiProps } from './sagemaker-endpoints-listall';
import { ListAllInferencesApi } from './sagemaker-inference-listall';
import { SagemakerInferenceProps, SagemakerInferenceStateMachine } from './sd-sagemaker-inference-state-machine';
import { DockerImageName, ECRDeployment } from '../cdk-ecr-deployment/lib';
import { AIGC_WEBUI_INFERENCE } from '../common/dockerImages';
import {DeleteInferenceJobsApi, DeleteInferenceJobsApiProps} from "../api/inferences/delete-inference-jobs";

/*
AWS CDK code to create API Gateway, Lambda and SageMaker inference endpoint for txt2img/img2img inference
based on Stable Diffusion. S3 is used to store large payloads and passed as object reference in the API Gateway
request and Lambda function to avoid request payload limitation
Note: Sync Inference is put here for reference, we use Async Inference now
*/
export interface SDAsyncInferenceStackProps extends StackProps {
  inferenceErrorTopic: sns.Topic;
  inferenceResultTopic: sns.Topic;
  routers: {[key: string]: Resource};
  s3_bucket: s3.Bucket;
  training_table: dynamodb.Table;
  multiUserTable: dynamodb.Table;
  snsTopic: aws_sns.Topic;
  ecr_image_tag: string;
  sd_inference_job_table: aws_dynamodb.Table;
  sd_endpoint_deployment_job_table: aws_dynamodb.Table;
  checkpointTable: aws_dynamodb.Table;
  commonLayer: PythonLayerVersion;
  useExist: string;
  authorizer: aws_apigateway.IAuthorizer;
}

export class SDAsyncInferenceStack extends NestedStack {
  constructor(
    scope: Construct,
    id: string,
    props: SDAsyncInferenceStackProps,
  ) {
    super(scope, id, props);
    if (!props?.ecr_image_tag) {
      throw new Error('default_inference_ecr_image is required');
    }
    const srcImg = AIGC_WEBUI_INFERENCE + props?.ecr_image_tag;

    const inferenceECR_url = this.createInferenceECR(srcImg);

    const sd_inference_job_table = props.sd_inference_job_table;
    const sd_endpoint_deployment_job_table = props.sd_endpoint_deployment_job_table;
    const inference = props.routers.inference;
    const inferV2Router = inference.addResource('v2');
    const srcRoot = '../middleware_api/lambda';
    new CreateInferenceJobApi(
      this, 'sd-infer-v2-create',
      <CreateInferenceJobApiProps>{
        checkpointTable: props.checkpointTable,
        commonLayer: props.commonLayer,
        endpointDeploymentTable: sd_endpoint_deployment_job_table,
        httpMethod: 'POST',
        inferenceJobTable: sd_inference_job_table,
        router: inferV2Router,
        s3Bucket: props.s3_bucket,
        srcRoot: srcRoot,
        multiUserTable: props.multiUserTable,
      },
    );

    new RunInferenceJobApi(
      this, 'sd-infer-v2-run',
      <RunInferenceJobApiProps>{
        checkpointTable: props.checkpointTable,
        commonLayer: props.commonLayer,
        endpointDeploymentTable: sd_endpoint_deployment_job_table,
        httpMethod: 'PUT',
        inferenceJobTable: sd_inference_job_table,
        router: inferV2Router,
        s3Bucket: props.s3_bucket,
        srcRoot: srcRoot,
      },
    );

    new ListAllSagemakerEndpointsApi(
      this, 'ListEndpoints',
        <ListAllSageMakerEndpointsApiProps>{
          router: props.routers.endpoints,
          commonLayer: props.commonLayer,
          endpointDeploymentTable: sd_endpoint_deployment_job_table,
          multiUserTable: props.multiUserTable,
          httpMethod: 'GET',
          srcRoot: srcRoot,
          authorizer: props.authorizer,
        },
    );

    new DeleteSagemakerEndpointsApi(
      this, 'sd-infer-v2-deleteEndpoints',
        <DeleteSagemakerEndpointsApiProps>{
          router: props.routers.endpoints,
          commonLayer: props.commonLayer,
          endpointDeploymentTable: sd_endpoint_deployment_job_table,
          multiUserTable: props.multiUserTable,
          httpMethod: 'DELETE',
          srcRoot: srcRoot,
          authorizer: props.authorizer,
        },
    );

    new SagemakerEndpointEvents(
      this, 'sd-infer-endpoint-events',
        <SagemakerEndpointEventsProps>{
          commonLayer: props.commonLayer,
          endpointDeploymentTable: sd_endpoint_deployment_job_table,
          multiUserTable: props.multiUserTable,
          srcRoot: srcRoot,
        },
    );

    new ListAllInferencesApi(
      this, 'ListInferenceJobs',
      {
        inferenceJobTable: sd_inference_job_table,
        authorizer: props.authorizer,
        commonLayer: props.commonLayer,
        endpointDeploymentTable: sd_endpoint_deployment_job_table,
        multiUserTable: props.multiUserTable,
        httpMethod: 'GET',
        router: props.routers.inferences,
        srcRoot: srcRoot,
      },
    );

    // Create an SNS topic to get async inference result
    const inference_result_topic = aws_sns.Topic.fromTopicArn(scope, `${id}-infer-result-tp`, props.inferenceResultTopic.topicArn);

    const inference_result_error_topic = aws_sns.Topic.fromTopicArn(scope, `${id}-infer-result-err-tp`, props.inferenceErrorTopic.topicArn);

    new CreateSagemakerEndpointsApi(
      this, 'sd-infer-v2-createEndpoint',
          <CreateSagemakerEndpointsApiProps>{
            router: props.routers.endpoints,
            commonLayer: props.commonLayer,
            endpointDeploymentTable: sd_endpoint_deployment_job_table,
            multiUserTable: props.multiUserTable,
            inferenceJobTable: sd_inference_job_table,
            httpMethod: 'POST',
            srcRoot: srcRoot,
            authorizer: props.authorizer,
            s3Bucket: props.s3_bucket,
            userNotifySNS: props.snsTopic,
            inferenceECRUrl: inferenceECR_url,
            inferenceResultTopic: inference_result_topic,
            inferenceResultErrorTopic: inference_result_error_topic,
          },
    );

    const stepFunctionStack = new SagemakerInferenceStateMachine(this, <SagemakerInferenceProps>{
      snsTopic: inference_result_topic,
      snsErrorTopic: inference_result_error_topic,
      s3_bucket: props.s3_bucket,
      inferenceJobTable: sd_inference_job_table,
      endpointDeploymentJobTable: sd_endpoint_deployment_job_table,
      userNotifySNS: props.snsTopic,
      inference_ecr_url: inferenceECR_url,
    });

    const inferenceLambdaRole = new iam.Role(this, 'InferenceLambdaRole', {
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
      this,
      'InferenceLambda',
      {
        code: lambda.DockerImageCode.fromImageAsset(
          '../middleware_api/lambda/inference',
        ),
        timeout: Duration.minutes(15),
        memorySize: 3008,
        environment: {
          DDB_INFERENCE_TABLE_NAME: sd_inference_job_table.tableName,
          DDB_TRAINING_TABLE_NAME:
                        props?.training_table.tableName ?? '',
          DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME:
                        sd_endpoint_deployment_job_table.tableName,
          S3_BUCKET: props?.s3_bucket.bucketName ?? '',
          ACCOUNT_ID: Aws.ACCOUNT_ID,
          REGION_NAME: Aws.REGION,
          SNS_INFERENCE_SUCCESS: inference_result_topic.topicName,
          SNS_INFERENCE_ERROR: inference_result_error_topic.topicName,
          STEP_FUNCTION_ARN: stepFunctionStack.stateMachineArn,
          NOTICE_SNS_TOPIC: props?.snsTopic.topicArn ?? '',
          INFERENCE_ECR_IMAGE_URL: inferenceECR_url,
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
    const stateMachineStatement = new iam.PolicyStatement({
      actions: [
        'states:StartExecution',
      ],
      resources: [stepFunctionStack.stateMachineArn],
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
      resources: [sd_endpoint_deployment_job_table.tableArn, sd_inference_job_table.tableArn],
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
        'arn:aws:s3:::*sagemaker*',
      ],
    });
    const snsStatement = new iam.PolicyStatement(<PolicyStatementProps>{
      actions: [
        'sns:Publish',
        'sns:ListTopics',
      ],
      resources: [props?.snsTopic.topicArn, inference_result_error_topic.topicArn, inference_result_topic.topicArn],
    });
    inferenceLambda.addToRolePolicy(ddbStatement);
    inferenceLambda.addToRolePolicy(s3Statement);
    inferenceLambda.addToRolePolicy(stateMachineStatement);
    inferenceLambda.addToRolePolicy(snsStatement);

    // Create a POST method for the API Gateway and connect it to the Lambda function
    const txt2imgIntegration = new apigw.LambdaIntegration(inferenceLambda);

    // The api can be invoked directly from the user's client code, the path starts with /api
    const inferenceApi = props.routers['inference-api'];
    const run_sagemaker_inference_api = inferenceApi.addResource(
      'inference',
    );

    new InferenceL2Api(
      this, 'sd-infer-l2-api',
      <InferenceL2ApiProps>{
        checkpointTable: props.checkpointTable,
        commonLayer: props.commonLayer,
        endpointDeploymentTable: sd_endpoint_deployment_job_table,
        httpMethod: 'POST',
        inferenceJobTable: sd_inference_job_table,
        router: run_sagemaker_inference_api,
        s3Bucket: props.s3_bucket,
        srcRoot: srcRoot,
      },
    );

      new DeleteInferenceJobsApi(
          this, 'DeleteInferenceJobs',
          <DeleteInferenceJobsApiProps>{
              router: props.routers.inferences,
              commonLayer: props.commonLayer,
              inferenceJobTable: sd_inference_job_table,
              httpMethod: 'DELETE',
              s3Bucket: props.s3_bucket,
              srcRoot: srcRoot,
          },
      );

    // Add a POST method with prefix inference
    if (!inference) {
      throw new Error('inference is undefined');
    }
    inference.addMethod('POST', txt2imgIntegration, {
      apiKeyRequired: true,
    });

    inference.addMethod('GET', txt2imgIntegration, {
      apiKeyRequired: true,
    });

    const run_sagemaker_inference = inference.addResource(
      'run-sagemaker-inference',
    );
    run_sagemaker_inference.addMethod('POST', txt2imgIntegration, {
      apiKeyRequired: true,
    });

    const deploy_sagemaker_endpoint = inference.addResource(
      'deploy-sagemaker-endpoint',
    );
    deploy_sagemaker_endpoint.addMethod('POST', txt2imgIntegration, <MethodOptions>{
      apiKeyRequired: true,
      authorizer: props.authorizer,
    });

    // const list_endpoint_deployment_jobs = inference.addResource(
    //   'list-endpoint-deployment-jobs',
    // );
    // list_endpoint_deployment_jobs.addMethod('GET', txt2imgIntegration, {
    //   apiKeyRequired: true,
    // });

    const delete_deployment_jobs = inference.addResource(
      'delete-sagemaker-endpoint');
    delete_deployment_jobs.addMethod('POST', txt2imgIntegration, <MethodOptions>{
      apiKeyRequired: true,
      authorizer: props.authorizer,
    });

    const list_inference_jobs = inference.addResource(
      'list-inference-jobs',
    );
    list_inference_jobs.addMethod('GET', txt2imgIntegration, {
      apiKeyRequired: true,
    });
    const query_inference_jobs = inference.addResource(
      'query-inference-jobs',
    );
    query_inference_jobs.addMethod('POST', txt2imgIntegration, {
      apiKeyRequired: true,
    });

    const get_endpoint_deployment_job = inference.addResource(
      'get-endpoint-deployment-job',
    );
    get_endpoint_deployment_job.addMethod('GET', txt2imgIntegration, {
      apiKeyRequired: true,
    });

    const get_inference_job = inference.addResource('get-inference-job');
    get_inference_job.addMethod('GET', txt2imgIntegration, {
      apiKeyRequired: true,
    });

    const get_texual_inversion_list = inference.addResource(
      'get-texual-inversion-list',
    );
    get_texual_inversion_list.addMethod('GET', txt2imgIntegration, {
      apiKeyRequired: true,
    });

    const get_lora_list = inference.addResource('get-lora-list');
    get_lora_list.addMethod('GET', txt2imgIntegration, {
      apiKeyRequired: true,
    });

    const get_hypernetwork_list = inference.addResource(
      'get-hypernetwork-list',
    );
    get_hypernetwork_list.addMethod('GET', txt2imgIntegration, {
      apiKeyRequired: true,
    });

    const get_controlnet_model_list = inference.addResource(
      'get-controlnet-model-list',
    );
    get_controlnet_model_list.addMethod('GET', txt2imgIntegration, {
      apiKeyRequired: true,
    });

    const get_inference_job_image_output = inference.addResource(
      'get-inference-job-image-output',
    );
    get_inference_job_image_output.addMethod('GET', txt2imgIntegration, {
      apiKeyRequired: true,
    });

    const get_inference_job_param_output = inference.addResource(
      'get-inference-job-param-output',
    );
    get_inference_job_param_output.addMethod('GET', txt2imgIntegration, {
      apiKeyRequired: true,
    });

    // fixme: this api is actually no needed anymore, delete later
    const test_output = inference.addResource('generate-s3-presigned-url-for-uploading');
    // test_output.addCorsPreflight({
    //   allowOrigins: apigw.Cors.ALL_ORIGINS,
    //   allowMethods: apigw.Cors.ALL_METHODS,
    //   allowHeaders: ['Content-Type', 'X-Amz-Date', 'Authorization', 'X-Api-Key', 'X-Amz-Security-Token', 'X-Amz-User-Agent'],
    // });

    test_output.addMethod('GET', txt2imgIntegration, {
      apiKeyRequired: true,
    });
    const testResource = inference.addResource('test-connection');
    const mockIntegration = new apigw.MockIntegration({
      integrationResponses: [
        {
          statusCode: '200',
          responseTemplates: {
            'application/json': JSON.stringify({
              message: 'Success',
            }),
          },
        },
      ],
      passthroughBehavior: apigw.PassthroughBehavior.NEVER,
      requestTemplates: {
        'application/json': '{"statusCode": 200}',
      },
    });

    testResource.addMethod('GET', mockIntegration, {
      methodResponses: [
        {
          statusCode: '200',
          responseModels: {
            'application/json': apigw.Model.EMPTY_MODEL,
          },
        },
      ],
      apiKeyRequired: true,
    });

    const handler = new python.PythonFunction(
      this,
      'InferenceResultNotification',
      {
        entry: path.join(
          __dirname,
          '../../../middleware_api/lambda/inference_result_notification',
        ),
        runtime: lambda.Runtime.PYTHON_3_9,
        handler: 'lambda_handler',
        index: 'app.py', // optional, defaults to 'index.py'
        memorySize: 256,
        timeout: Duration.seconds(900),
        environment: {
          DDB_INFERENCE_TABLE_NAME: sd_inference_job_table.tableName,
          DDB_TRAINING_TABLE_NAME: props?.training_table.tableName ?? '',
          DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME: sd_endpoint_deployment_job_table.tableName,
          S3_BUCKET: props?.s3_bucket.bucketName ?? '',
          ACCOUNT_ID: Aws.ACCOUNT_ID,
          REGION_NAME: Aws.REGION,
          SNS_INFERENCE_SUCCESS: inference_result_topic.topicName,
          SNS_INFERENCE_ERROR: inference_result_error_topic.topicName,
          STEP_FUNCTION_ARN: stepFunctionStack.stateMachineArn,
          NOTICE_SNS_TOPIC: props?.snsTopic.topicArn ?? '',
          INFERENCE_ECR_IMAGE_URL: inferenceECR_url,
        },
        bundling: {
          buildArgs: {
            PIP_INDEX_URL: 'https://pypi.org/simple/',
            PIP_EXTRA_INDEX_URL: 'https://pypi.org/simple/',
          },
        },
        logRetention: RetentionDays.ONE_WEEK,
      },
    );

    handler.addToRolePolicy(s3Statement);
    handler.addToRolePolicy(ddbStatement);
    handler.addToRolePolicy(snsStatement);

    //adding model to data directory of s3 bucket
    if (props?.s3_bucket != undefined) {
      this.uploadModelToS3(props.s3_bucket);
    }

    // Add the SNS topic as an event source for the Lambda function
    handler.addEventSource(
      new eventSources.SnsEventSource(inference_result_topic),
    );
    handler.addEventSource(
      new eventSources.SnsEventSource(inference_result_error_topic),
    );
  }

  private createInferenceECR(srcImg: string) {
    const dockerRepo = new aws_ecr.Repository(
      this,
      'aigc-webui-inference-repo',
      {
        repositoryName: 'stable-diffusion-aws-extension/aigc-webui-inference',
        removalPolicy: RemovalPolicy.DESTROY,
      },
    );

    const ecrDeployment = new ECRDeployment(
      this,
      'aigc-webui-inference-ecr-deploy',
      {
        src: new DockerImageName(srcImg),
        dest: new DockerImageName(`${dockerRepo.repositoryUri}:latest`),
      },
    );

    // trigger the custom resource lambda
    const customJob = new CustomResource(
      this,
      'aigc-webui-inference-ecr-cr-image',
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

  private uploadModelToS3(s3_bucket: s3.Bucket) {
    // Create a folder in the bucket
    const folderKey = 'data/';

    // Upload a local file to the created folder
    console.log(__dirname);
    const modelPath = path.resolve(__dirname, '../', '../', 'models', 'model.zip');
    new s3deploy.BucketDeployment(this, 'DeployLocalFile', {
      sources: [s3deploy.Source.asset(modelPath)],
      destinationBucket: s3_bucket,
      destinationKeyPrefix: folderKey,
      retainOnDelete: false,
    });
  }
}
