import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, CfnParameter, Duration } from 'aws-cdk-lib';
import {
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
import { ICfnRuleConditionExpression } from 'aws-cdk-lib/core/lib/cfn-condition';

export const ESDRoleForEndpoint = 'ESDRoleForEndpoint';

export interface CreateEndpointApiProps {
  router: Resource;
  httpMethod: string;
  endpointDeploymentTable: Table;
  multiUserTable: Table;
  srcRoot: string;
  commonLayer: LayerVersion;
  s3Bucket: Bucket;
  userNotifySNS: Topic;
  inferenceResultTopic: Topic;
  inferenceResultErrorTopic: Topic;
  logLevel: CfnParameter;
  ecrImageTag: CfnParameter;
  accountId: ICfnRuleConditionExpression;
}

export class CreateEndpointApi {
  public model: Model;
  public requestValidator: RequestValidator;
  private readonly src: string;
  private readonly router: Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly endpointDeploymentTable: Table;
  private readonly multiUserTable: Table;
  private readonly layer: LayerVersion;
  private readonly baseId: string;
  private readonly ecrImageTag: CfnParameter;
  private readonly accountId: ICfnRuleConditionExpression;
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
    this.multiUserTable = props.multiUserTable;
    this.src = props.srcRoot;
    this.layer = props.commonLayer;
    this.s3Bucket = props.s3Bucket;
    this.userNotifySNS = props.userNotifySNS;
    this.inferenceResultTopic = props.inferenceResultTopic;
    this.inferenceResultErrorTopic = props.inferenceResultErrorTopic;
    this.logLevel = props.logLevel;
    this.ecrImageTag = props.ecrImageTag;
    this.accountId = props.accountId;
    this.model = this.createModel();
    this.requestValidator = this.createRequestValidator();

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
        // for get files from solution's bucket
        '*',
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

  private createModel(): Model {
    return new Model(this.scope, `${this.baseId}-model`, {
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
            maxLength: 20,
          },
          custom_docker_image_uri: {
            type: JsonSchemaType.STRING,
          },
          endpoint_type: {
            type: JsonSchemaType.STRING,
            enum: ['Real-time', 'Serverless', 'Async'],
          },
          cool_down_time: {
            type: JsonSchemaType.STRING,
            enum: ['15 minutes', '1 hour', '6 hours', '1 day'],
          },
          instance_type: {
            type: JsonSchemaType.STRING,
          },
          initial_instance_count: {
            type: JsonSchemaType.NUMBER,
            minimum: 1,
          },
          min_instance_number: {
            type: JsonSchemaType.NUMBER,
            minimum: 0,
          },
          max_instance_number: {
            type: JsonSchemaType.NUMBER,
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
          'endpoint_type',
          'instance_type',
          'initial_instance_count',
          'autoscaling_enabled',
          'assign_to_roles',
          'creator',
        ],
      },
    });
  }

  private createRequestValidator(): RequestValidator {
    return new RequestValidator(this.scope, `${this.baseId}-create-ep-validator`, {
      restApi: this.router.api,
      validateRequestBody: true,
      validateRequestParameters: false,
    });
  }

  private createEndpointsApi() {

    const role = this.iamRole();

    const lambdaFunction = new PythonFunction(this.scope, `${this.baseId}-lambda`, {
      entry: `${this.src}/endpoints`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'create_endpoint.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: role,
      memorySize: 2048,
      environment: {
        DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME: this.endpointDeploymentTable.tableName,
        MULTI_USER_TABLE: this.multiUserTable.tableName,
        S3_BUCKET_NAME: this.s3Bucket.bucketName,
        INFERENCE_ECR_IMAGE_URL: `${this.accountId.toString()}.dkr.ecr.${Aws.REGION}.${Aws.URL_SUFFIX}/esd-inference:${this.ecrImageTag.valueAsString}`,
        ECR_IMAGE_TAG: this.ecrImageTag.valueAsString,
        SNS_INFERENCE_SUCCESS: this.inferenceResultTopic.topicArn,
        SNS_INFERENCE_ERROR: this.inferenceResultErrorTopic.topicArn,
        EXECUTION_ROLE_ARN: role.roleArn,
        LOG_LEVEL: this.logLevel.valueAsString,
      },
      layers: [this.layer],
    });


    const integration = new LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );


    this.router.addMethod(this.httpMethod, integration, <MethodOptions>{
      apiKeyRequired: true,
      requestValidator: this.requestValidator,
      requestModels: {
        'application/json': this.model,
      },
    });

  }
}
