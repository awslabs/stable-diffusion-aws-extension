import * as python from '@aws-cdk/aws-lambda-python-alpha';
import { PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, aws_dynamodb, aws_sns, CfnParameter, Duration, StackProps } from 'aws-cdk-lib';
import { Resource } from 'aws-cdk-lib/aws-apigateway/lib/resource';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as eventSources from 'aws-cdk-lib/aws-lambda-event-sources';
import { RetentionDays } from 'aws-cdk-lib/aws-logs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Size } from 'aws-cdk-lib/core';
import { ICfnRuleConditionExpression } from 'aws-cdk-lib/core/lib/cfn-condition';
import { Construct } from 'constructs';
import { ResourceProvider } from './resource-provider';
import { CreateInferenceJobApi } from '../api/inferences/create-inference-job';
import { DeleteInferenceJobsApi } from '../api/inferences/delete-inference-jobs';
import { GetInferenceJobApi } from '../api/inferences/get-inference-job';
import { ListInferencesApi } from '../api/inferences/list-inferences';
import { StartInferenceJobApi } from '../api/inferences/start-inference-job';
import { EndpointStack, EndpointStackProps } from '../endpoints/endpoint-stack';

/*
AWS CDK code to create API Gateway, Lambda and SageMaker inference endpoint for txt2img/img2img inference
based on Stable Diffusion. S3 is used to store large payloads and passed as object reference in the API Gateway
request and Lambda function to avoid request payload limitation
Note: Sync Inference is put here for reference, we use Async Inference now
*/
export interface InferenceProps extends StackProps {
  inferenceErrorTopic: aws_sns.Topic;
  inferenceResultTopic: aws_sns.Topic;
  routers: { [key: string]: Resource };
  s3_bucket: s3.Bucket;
  training_table: aws_dynamodb.Table;
  multiUserTable: aws_dynamodb.Table;
  snsTopic: aws_sns.Topic;
  ecr_image_tag: CfnParameter;
  sd_inference_job_table: aws_dynamodb.Table;
  sd_endpoint_deployment_job_table: aws_dynamodb.Table;
  checkpointTable: aws_dynamodb.Table;
  commonLayer: PythonLayerVersion;
  logLevel: CfnParameter;
  resourceProvider: ResourceProvider;
  accountId: ICfnRuleConditionExpression;
}

export class Inference {

  constructor(
    scope: Construct,
    props: InferenceProps,
  ) {

    const inference = props.routers.inference;
    const inferV2Router = props.routers.inferences.addResource('{id}');
    const srcRoot = '../middleware_api/lambda';

    const createInferenceJobApi = new CreateInferenceJobApi(
      scope, 'CreateInferenceJob', {
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
      scope, 'StartInferenceJob', {
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
              commonLayer: props.commonLayer,
              logLevel: props.logLevel,
              accountId: props.accountId,
              ecrImageTag: props.ecr_image_tag,
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

    const snsStatement = new iam.PolicyStatement({
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

    new GetInferenceJobApi(scope, 'GetInferenceJob', {
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

    const deleteInferenceJobsApi = new DeleteInferenceJobsApi(
      scope, 'DeleteInferenceJobs', {
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

    const handler = new python.PythonFunction(scope, 'InferenceResultNotification', {
      entry: `${srcRoot}/inferences`,
      runtime: lambda.Runtime.PYTHON_3_10,
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
}
