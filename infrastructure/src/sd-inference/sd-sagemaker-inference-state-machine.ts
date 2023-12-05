// Import the required CDK modules
import * as path from 'path';
import {
  Duration, aws_sns as sns, Aws,
} from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as stepfunctions from 'aws-cdk-lib/aws-stepfunctions';
import * as stepfunctionsTasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import { SnsPublishProps } from 'aws-cdk-lib/aws-stepfunctions-tasks';
import { Construct } from 'constructs';
import { LAMBDA_START_DEPLOY_ROLE_NAME } from '../shared/deploy-role';


export interface SagemakerInferenceProps {
  snsTopic: sns.Topic;
  snsErrorTopic: sns.Topic;
  s3_bucket: s3.Bucket;
  inferenceJobTable: dynamodb.Table;
  endpointDeploymentJobTable: dynamodb.Table;
  userNotifySNS: sns.Topic;
  inference_ecr_url: string;
}

export class SagemakerInferenceStateMachine {
  public readonly stateMachineArn: string;
  private readonly scope: Construct;

  constructor(scope: Construct, props: SagemakerInferenceProps) {
    this.scope = scope;
    this.stateMachineArn = this.sagemakerStepFunction(
      props.snsTopic,
      props.snsErrorTopic,
      props.s3_bucket,
      props.inferenceJobTable,
      props.endpointDeploymentJobTable,
      props.userNotifySNS,
      props.inference_ecr_url,
    ).stateMachineArn;
  }

  private sagemakerStepFunction(
    snsTopic: sns.Topic,
    snsErrorTopic: sns.Topic,
    s3Bucket: s3.Bucket,
    inferenceJobTable: dynamodb.Table,
    endpointDeploymentJobTable: dynamodb.Table,
    userNotifySNS: sns.Topic,
    inference_ecr_url: string,
  ): stepfunctions.StateMachine {
    const lambdaPolicy = // Grant Lambda permission to invoke SageMaker endpoint
            new iam.PolicyStatement({
              actions: [
                'logs:CreateLogGroup',
                'logs:CreateLogStream',
                'logs:PutLogEvents',
                'lambda:GetFunctionConfiguration',
                's3:ListBucket',
                's3:GetObject',
              ],
              resources: ['*'],
            });

    const endpointStatement = new iam.PolicyStatement({
      actions: [
        'sagemaker:InvokeEndpoint',
        'sagemaker:CreateModel',
        'sagemaker:CreateEndpoint',
        'sagemaker:CreateEndpointConfig',
        'sagemaker:DescribeEndpoint',
        'sagemaker:InvokeEndpointAsync',
        'ecr:GetAuthorizationToken',
        'ecr:BatchCheckLayerAvailability',
        'ecr:GetDownloadUrlForLayer',
        'ecr:GetRepositoryPolicy',
        'ecr:DescribeRepositories',
        'ecr:ListImages',
        'ecr:DescribeImages',
        'ecr:BatchGetImage',
        'ecr:InitiateLayerUpload',
        'ecr:UploadLayerPart',
        'ecr:CompleteLayerUpload',
        'ecr:PutImage',
        'cloudwatch:PutMetricAlarm',
        'cloudwatch:PutMetricData',
        'sagemaker:DescribeEndpointConfig',
        'cloudwatch:DeleteAlarms',
        'cloudwatch:DescribeAlarms',
        'sagemaker:UpdateEndpointWeightsAndCapacities',
        'iam:CreateServiceLinkedRole',
      ],
      resources: ['*'],
    });

    const s3Statement = new iam.PolicyStatement({
      actions: [
        's3:Get*',
        's3:List*',
        's3:PutObject',
        's3:GetObject',
      ],
      resources: [
        s3Bucket.bucketArn,
        `${s3Bucket.bucketArn}/*`,
        `arn:${Aws.PARTITION}:s3:::*sagemaker*`,
      ],
    });

    const snsStatement = new iam.PolicyStatement({
      actions: [
        'sns:Publish',
        'sns:ListSubscriptionsByTopic',
        'sns:ListTopics',
      ],
      resources: [snsTopic.topicArn, snsErrorTopic.topicArn, userNotifySNS.topicArn],
    });

    const endpointAutoScalingStatement = new iam.PolicyStatement({
      actions: [
        'application-autoscaling:RegisterScalableTarget',
        'application-autoscaling:PutScalingPolicy',
      ],
      resources: ['*'],
    });

    const ddbStatement = new iam.PolicyStatement({
      actions: [
        'dynamodb:UpdateItem',
        'dynamodb:PutItem',
        'dynamodb:BatchGetItem',
        'dynamodb:Describe*',
        'dynamodb:List*',
        'dynamodb:GetItem',
        'dynamodb:Query',
        'dynamodb:Scan',
      ],
      resources: [inferenceJobTable.tableArn, endpointDeploymentJobTable.tableArn],
    });

    const lambdaErrorHandlerRole = new iam.Role(this.scope, 'LambdaErrorHandlerRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
    });

    lambdaErrorHandlerRole.addToPolicy(lambdaPolicy);
    lambdaErrorHandlerRole.addToPolicy(snsStatement);
    lambdaErrorHandlerRole.addToPolicy(s3Statement);
    lambdaErrorHandlerRole.addToPolicy(endpointStatement);
    lambdaErrorHandlerRole.addToPolicy(ddbStatement);
    lambdaErrorHandlerRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          'iam:PassRole',
        ],
        resources: [lambdaErrorHandlerRole.roleArn],
      }),
    );

    const lambdaErrorHandler = new lambda.Function(
      this.scope,
      'InferenceWorkflowErrorHandler',
      {
        runtime: lambda.Runtime.PYTHON_3_9,
        handler: 'app.lambda_handler',
        code: lambda.Code.fromAsset(
          path.join(
            __dirname,
            '../../../middleware_api/lambda/endpoint_creation_workflow_error_handler',
          ),
        ),
        // Add any environment variables needed for the error handler Lambda
        environment: {
          SNS_INFERENCE_SUCCESS: snsTopic.topicArn,
          SNS_INFERENCE_ERROR: snsErrorTopic.topicArn,
          DDB_INFERENCE_TABLE_NAME: inferenceJobTable.tableName,
          DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME: endpointDeploymentJobTable.tableName,
          SNS_NOTIFY_TOPIC_ARN: userNotifySNS.topicArn,
          S3_BUCKET_NAME: s3Bucket.bucketName,
          INFERENCE_ECR_IMAGE_URL: inference_ecr_url,
        },
        role: lambdaErrorHandlerRole,
        timeout: Duration.seconds(900),
      },
    );

    const lambdaStartDeployRole = <iam.Role>iam.Role.fromRoleName(
      this.scope,
      'LambdaStartDeployRole',
      LAMBDA_START_DEPLOY_ROLE_NAME,
    );
    lambdaStartDeployRole.addToPolicy(lambdaPolicy);
    lambdaStartDeployRole.addToPolicy(snsStatement);
    lambdaStartDeployRole.addToPolicy(s3Statement);
    lambdaStartDeployRole.addToPolicy(endpointStatement);
    lambdaStartDeployRole.addToPolicy(ddbStatement);
    lambdaStartDeployRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          'iam:PassRole',
        ],
        resources: [lambdaStartDeployRole.roleArn],
      }),
    );

    // Define the Lambda functions
    const lambdaStartDeploy = new lambda.Function(
      this.scope,
      'LambdaModelDeploy',
      {
        runtime: lambda.Runtime.PYTHON_3_9,
        handler: 'app.lambda_handler',
        code: lambda.Code.fromAsset(
          path.join(
            __dirname,
            '../../../middleware_api/lambda/start_endpoint_deployment',
          ),
        ),
        environment: {
          SNS_INFERENCE_SUCCESS: snsTopic.topicArn,
          SNS_INFERENCE_ERROR: snsErrorTopic.topicArn,
          DDB_INFERENCE_TABLE_NAME: inferenceJobTable.tableName,
          DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME: endpointDeploymentJobTable.tableName,
          SNS_NOTIFY_TOPIC_ARN: userNotifySNS.topicArn,
          S3_BUCKET_NAME: s3Bucket.bucketName,
          INFERENCE_ECR_IMAGE_URL: inference_ecr_url,
        },
        role: lambdaStartDeployRole,
        timeout: Duration.seconds(900),
      },
    );

    const lambdaCheckDeploymentStatusRole = new iam.Role(this.scope, 'LambdaCheckDeploymentStatusRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
    });

    lambdaCheckDeploymentStatusRole.addToPolicy(lambdaPolicy);
    lambdaCheckDeploymentStatusRole.addToPolicy(snsStatement);
    lambdaCheckDeploymentStatusRole.addToPolicy(s3Statement);
    lambdaCheckDeploymentStatusRole.addToPolicy(endpointStatement);
    lambdaCheckDeploymentStatusRole.addToPolicy(ddbStatement);
    lambdaCheckDeploymentStatusRole.addToPolicy(endpointAutoScalingStatement);
    lambdaCheckDeploymentStatusRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          'iam:PassRole',
        ],
        resources: [lambdaCheckDeploymentStatusRole.roleArn],
      }),
    );

    const lambdaCheckDeploymentStatus = new lambda.Function(
      this.scope,
      'LambdaModelAwait',
      {
        runtime: lambda.Runtime.PYTHON_3_9,
        handler: 'app.lambda_handler',
        code: lambda.Code.fromAsset(
          path.join(
            __dirname,
            '../../../middleware_api/lambda/check_endpoint_deployment',
          ),
        ),
        environment: {
          SNS_INFERENCE_SUCCESS: snsTopic.topicName,
          SNS_INFERENCE_ERROR: snsErrorTopic.topicName,
          DDB_INFERENCE_TABLE_NAME: inferenceJobTable.tableName,
          DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME: endpointDeploymentJobTable.tableName,
          SNS_NOTIFY_TOPIC_ARN: userNotifySNS.topicArn,
          S3_BUCKET_NAME: s3Bucket.bucketName,
          INFERENCE_ECR_IMAGE_URL: inference_ecr_url,
        },
        role: lambdaCheckDeploymentStatusRole,
        timeout: Duration.seconds(30),
      },
    );

    //TODO: still not working for assume sagemaker service, need to work it later
    // Add the trust relationship for SageMaker service principal to both Lambda roles
    const sagemakerAssumeRolePolicy = new iam.PolicyStatement({
      actions: ['sts:AssumeRole'],
      effect: iam.Effect.ALLOW,
      principals: [new iam.ServicePrincipal('sagemaker.amazonaws.com')],
    });

    (lambdaStartDeploy.role as iam.Role).assumeRolePolicy?.addStatements(sagemakerAssumeRolePolicy);
    (lambdaCheckDeploymentStatus.role as iam.Role).assumeRolePolicy?.addStatements(sagemakerAssumeRolePolicy);
    lambdaCheckDeploymentStatus.role?.grant(new iam.ServicePrincipal('sagemaker.amazonaws.com'));


    // Define the Step Functions tasks
    const errorHandlerTask = new stepfunctionsTasks.LambdaInvoke(
      this.scope,
      'ErrorHandlerTask',
      {
        lambdaFunction: lambdaErrorHandler,
      },
    );

    const startDeploymentTask = new stepfunctionsTasks.LambdaInvoke(
      this.scope,
      'StartDeployment',
      {
        lambdaFunction: lambdaStartDeploy,
      },
    ).addCatch(errorHandlerTask, {
      errors: ['States.ALL'],
      resultPath: '$.error',
    });

    const checkStatusDeploymentTask = new stepfunctionsTasks.LambdaInvoke(
      this.scope,
      'CheckStatusDeployment',
      {
        lambdaFunction: lambdaCheckDeploymentStatus,
      },
    ).addCatch(errorHandlerTask, {
      errors: ['States.ALL'],
      resultPath: '$.error',
    });

    const checkDeploymentBranch = new stepfunctions.Choice(
      this.scope,
      'CheckDeploymentBranch',
    );

    const waitStatusDeploymentTask = new stepfunctions.Wait(
      this.scope,
      'WaitStatusDeployment',
      {
        time: stepfunctions.WaitTime.duration(Duration.minutes(2)),
      },
    );

    // Step to send SNS notification
    const sendNotification = new stepfunctionsTasks.SnsPublish(
      this.scope,
      'SendNotification',
            <SnsPublishProps>{
              topic: snsTopic,
              message: stepfunctions.TaskInput.fromText(
                'EndPoint Creation job completed',
              ),
            },
    );

    // Define the Step Functions state machine
    const stateMachineDefinition = startDeploymentTask
      .next(checkStatusDeploymentTask)
      .next(
        checkDeploymentBranch
          .when(
            stepfunctions.Condition.stringEquals(
              '$.Payload.status',
              'Creating',
            ),
            waitStatusDeploymentTask.next(checkStatusDeploymentTask),
          )
          .when(
            stepfunctions.Condition.stringEquals(
              '$.Payload.status',
              'InService',
            ),
            sendNotification,
          )
          .afterwards(),
      );

    return new stepfunctions.StateMachine(this.scope, 'StateMachine', {
      definition: stateMachineDefinition,
    });
  }
}
