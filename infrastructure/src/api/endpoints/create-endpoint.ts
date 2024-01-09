import { PythonFunction, PythonFunctionProps } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, CfnParameter, Duration } from 'aws-cdk-lib';
import {
  IAuthorizer,
  JsonSchemaType,
  JsonSchemaVersion,
  LambdaIntegration,
  Model,
  RequestValidator,
  Resource,
} from 'aws-cdk-lib/aws-apigateway';
import { MethodOptions } from 'aws-cdk-lib/aws-apigateway/lib/method';
import { Table } from 'aws-cdk-lib/aws-dynamodb';
import { CompositePrincipal, Effect, PolicyStatement, Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';
import { Architecture, LayerVersion, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Bucket } from 'aws-cdk-lib/aws-s3';
import { Topic } from 'aws-cdk-lib/aws-sns';
import { Construct } from 'constructs';

export const ESDRoleForEndpoint = 'ESDRoleForEndpoint';

export interface CreateEndpointApiProps {
  router: Resource;
  httpMethod: string;
  endpointDeploymentTable: Table;
  multiUserTable: Table;
  inferenceJobTable: Table;
  srcRoot: string;
  inferenceECRUrl: string;
  commonLayer: LayerVersion;
  authorizer: IAuthorizer;
  s3Bucket: Bucket;
  userNotifySNS: Topic;
  inferenceResultTopic: Topic;
  inferenceResultErrorTopic: Topic;
  logLevel: CfnParameter;
}

export class CreateEndpointApi {
  private readonly src: string;
  private readonly router: Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly endpointDeploymentTable: Table;
  private readonly multiUserTable: Table;
  private readonly inferenceJobTable: Table;
  private readonly layer: LayerVersion;
  private readonly baseId: string;
  private readonly inferenceECRUrl: string;
  private readonly authorizer: IAuthorizer;
  private readonly s3Bucket: Bucket;
  private readonly userNotifySNS: Topic;
  private readonly inferenceResultTopic: Topic;
  private readonly inferenceResultErrorTopic: Topic;
  private readonly logLevel: CfnParameter;

  constructor(scope: Construct, id: string, props: CreateEndpointApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.endpointDeploymentTable = props.endpointDeploymentTable;
    this.inferenceJobTable = props.inferenceJobTable;
    this.multiUserTable = props.multiUserTable;
    this.authorizer = props.authorizer;
    this.src = props.srcRoot;
    this.layer = props.commonLayer;
    this.s3Bucket = props.s3Bucket;
    this.inferenceECRUrl = props.inferenceECRUrl;
    this.userNotifySNS = props.userNotifySNS;
    this.inferenceResultTopic = props.inferenceResultTopic;
    this.inferenceResultErrorTopic = props.inferenceResultErrorTopic;
    this.logLevel = props.logLevel;

    this.createEndpointsApi();
  }

  private iamRole(): Role {

    const snsStatement = new PolicyStatement({
      actions: [
        'sns:Publish',
        'sns:ListSubscriptionsByTopic',
        'sns:ListTopics',
      ],
      resources: [
        this.userNotifySNS.topicArn,
        this.inferenceResultTopic.topicArn,
        this.inferenceResultErrorTopic.topicArn,
      ],
    });

    const s3Statement = new PolicyStatement({
      actions: [
        's3:Get*',
        's3:List*',
        's3:PutObject',
        's3:GetObject',
      ],
      resources: [
        this.s3Bucket.bucketArn,
        `${this.s3Bucket.bucketArn}/*`,
        `arn:${Aws.PARTITION}:s3:::*sagemaker*`,
      ],
    });

    const endpointStatement = new PolicyStatement({
      actions: [
        'sagemaker:DeleteModel',
        'sagemaker:DeleteEndpoint',
        'sagemaker:DescribeEndpoint',
        'sagemaker:DeleteEndpointConfig',
        'sagemaker:DescribeEndpointConfig',
        'sagemaker:InvokeEndpoint',
        'sagemaker:CreateModel',
        'sagemaker:CreateEndpoint',
        'sagemaker:CreateEndpointConfig',
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
        'cloudwatch:DeleteAlarms',
        'cloudwatch:DescribeAlarms',
        'sagemaker:UpdateEndpointWeightsAndCapacities',
        'iam:CreateServiceLinkedRole',
        'iam:PassRole',
        'sts:AssumeRole',
      ],
      resources: ['*'],
    });

    const ddbStatement = new PolicyStatement({
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
        this.endpointDeploymentTable.tableArn,
        this.multiUserTable.tableArn,
        this.inferenceJobTable.tableArn,
      ],
    });

    const logStatement = new PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'logs:CreateLogGroup',
        'logs:CreateLogStream',
        'logs:PutLogEvents',
      ],
      resources: [`arn:${Aws.PARTITION}:logs:${Aws.REGION}:${Aws.ACCOUNT_ID}:log-group:*:*`],
    });

    const passStartDeployRole = new PolicyStatement({
      actions: [
        'iam:PassRole',
      ],
      resources: [
        `arn:${Aws.PARTITION}:iam::${Aws.ACCOUNT_ID}:role/${ESDRoleForEndpoint}-${Aws.REGION}`,
      ],
    });

    const lambdaStartDeployRole = new Role(this.scope, ESDRoleForEndpoint, {
      assumedBy: new CompositePrincipal(
        new ServicePrincipal('lambda.amazonaws.com'),
        new ServicePrincipal('sagemaker.amazonaws.com'),
      ),
      roleName: `${ESDRoleForEndpoint}-${Aws.REGION}`,
    });

    lambdaStartDeployRole.addToPolicy(snsStatement);
    lambdaStartDeployRole.addToPolicy(s3Statement);
    lambdaStartDeployRole.addToPolicy(endpointStatement);
    lambdaStartDeployRole.addToPolicy(ddbStatement);
    lambdaStartDeployRole.addToPolicy(logStatement);
    lambdaStartDeployRole.addToPolicy(passStartDeployRole);

    return lambdaStartDeployRole;
  }

  private createEndpointsApi() {

    const role = this.iamRole();

    const lambdaFunction = new PythonFunction(this.scope, `${this.baseId}-lambda`, <PythonFunctionProps>{
      entry: `${this.src}/endpoints`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_9,
      index: 'create_endpoint.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: role,
      memorySize: 1024,
      environment: {
        DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME: this.endpointDeploymentTable.tableName,
        MULTI_USER_TABLE: this.multiUserTable.tableName,
        S3_BUCKET_NAME: this.s3Bucket.bucketName,
        INFERENCE_ECR_IMAGE_URL: this.inferenceECRUrl,
        SNS_INFERENCE_SUCCESS: this.inferenceResultTopic.topicArn,
        SNS_INFERENCE_ERROR: this.inferenceResultErrorTopic.topicArn,
        EXECUTION_ROLE_ARN: role.roleArn,
        LOG_LEVEL: this.logLevel.valueAsString,
      },
      layers: [this.layer],
    });

    const model = new Model(this.scope, `${this.baseId}-model`, {
      restApi: this.router.api,
      contentType: 'application/json',
      modelName: this.baseId,
      description: `${this.baseId} Request Model`,
      schema: {
        schema: JsonSchemaVersion.DRAFT4,
        title: this.baseId,
        type: JsonSchemaType.OBJECT,
        properties: {
          endpoint_name: {
            type: JsonSchemaType.STRING,
            minLength: 0,
            maxLength: 20,
          },
          instance_type: {
            type: JsonSchemaType.STRING,
          },
          initial_instance_count: {
            type: JsonSchemaType.NUMBER,
            minimum: 1,
          },
          autoscaling_enabled: {
            type: JsonSchemaType.BOOLEAN,
          },
          assign_to_roles: {
            type: JsonSchemaType.ARRAY,
            items: {
              type: JsonSchemaType.STRING,
            },
            minItems: 1,
            maxItems: 10,
          },
          creator: {
            type: JsonSchemaType.STRING,
          },
        },
        required: [
          'instance_type',
          'initial_instance_count',
          'autoscaling_enabled',
          'assign_to_roles',
          'creator',
        ],
      },
    });

    const integration = new LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    const requestValidator = new RequestValidator(this.scope, `${this.baseId}-validator`, {
      restApi: this.router.api,
      requestValidatorName: this.baseId,
      validateRequestBody: true,
      validateRequestParameters: false,
    });

    this.router.addMethod(this.httpMethod, integration, <MethodOptions>{
      apiKeyRequired: true,
      authorizer: this.authorizer,
      requestValidator,
      requestModels: {
        'application/json': model,
      },
    });

  }
}
