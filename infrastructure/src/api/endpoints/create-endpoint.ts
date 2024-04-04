import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, aws_dynamodb, aws_iam, aws_lambda, aws_sqs, Duration } from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model, RequestValidator, Resource } from 'aws-cdk-lib/aws-apigateway';
import { Table } from 'aws-cdk-lib/aws-dynamodb';
import { CompositePrincipal, Effect, PolicyStatement, Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';
import { Architecture, LayerVersion, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Topic } from 'aws-cdk-lib/aws-sns';
import { ICfnRuleConditionExpression } from 'aws-cdk-lib/core/lib/cfn-condition';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import { SCHEMA_DEBUG, SCHEMA_MESSAGE } from '../../shared/schema';
import { ESD_VERSION } from '../../shared/version';

export const ESDRoleForEndpoint = 'ESDRoleForEndpoint';

export interface CreateEndpointApiProps {
  router: Resource;
  httpMethod: string;
  endpointDeploymentTable: Table;
  multiUserTable: Table;
  syncTable: aws_dynamodb.Table;
  instanceMonitorTable: aws_dynamodb.Table;
  commonLayer: LayerVersion;
  userNotifySNS: Topic;
  inferenceResultTopic: Topic;
  inferenceResultErrorTopic: Topic;
  queue: aws_sqs.Queue;
  accountId: ICfnRuleConditionExpression;
  executeResultSuccessTopic: Topic;
  executeResultFailTopic: Topic;
}

export class CreateEndpointApi {
  private readonly router: Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly endpointDeploymentTable: Table;
  private readonly multiUserTable: Table;
  private readonly syncTable: Table;
  private readonly instanceMonitorTable: Table;
  private readonly layer: LayerVersion;
  private readonly baseId: string;
  private readonly accountId: ICfnRuleConditionExpression;
  private readonly userNotifySNS: Topic;
  private readonly queue: aws_sqs.Queue;
  private readonly inferenceResultTopic: Topic;
  private readonly inferenceResultErrorTopic: Topic;
  private readonly executeResultSuccessTopic: Topic;
  private readonly executeResultFailTopic: Topic;

  constructor(scope: Construct, id: string, props: CreateEndpointApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.endpointDeploymentTable = props.endpointDeploymentTable;
    this.multiUserTable = props.multiUserTable;
    this.syncTable = props.syncTable;
    this.instanceMonitorTable = props.instanceMonitorTable;
    this.layer = props.commonLayer;
    this.userNotifySNS = props.userNotifySNS;
    this.inferenceResultTopic = props.inferenceResultTopic;
    this.inferenceResultErrorTopic = props.inferenceResultErrorTopic;
    this.executeResultSuccessTopic = props.executeResultSuccessTopic;
    this.executeResultFailTopic = props.executeResultFailTopic;
    this.queue = props.queue;
    this.accountId = props.accountId;

    const lambdaFunction = this.apiLambda();

    const integration = new LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.addMethod(this.httpMethod, integration, {
      apiKeyRequired: true,
      requestValidator: this.createRequestValidator(),
      requestModels: {
        'application/json': this.createModel(),
      },
      operationName: 'CreateEndpoint',
      methodResponses: [
        ApiModels.methodResponse(this.responseModel(), '202'),
        ApiModels.methodResponses401(),
        ApiModels.methodResponses403(),
        ApiModels.methodResponses404(),
      ],
    });
  }

  private responseModel() {
    return new Model(this.scope, `${this.baseId}-resp-model`, {
      restApi: this.router.api,
      modelName: 'CreateEndpointResponse',
      description: `${this.baseId} Response Model`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        type: JsonSchemaType.OBJECT,
        title: 'CreateEndpointResponse',
        properties: {
          statusCode: {
            type: JsonSchemaType.INTEGER,
            enum: [
              202,
            ],
          },
          debug: SCHEMA_DEBUG,
          message: SCHEMA_MESSAGE,
          data: {
            type: JsonSchemaType.OBJECT,
            properties: {
              EndpointDeploymentJobId: {
                type: JsonSchemaType.STRING,
                format: 'uuid',
              },
              autoscaling: {
                type: JsonSchemaType.BOOLEAN,
              },
              max_instance_number: {
                type: JsonSchemaType.STRING,
                pattern: '^[0-9]+$',
              },
              startTime: {
                type: JsonSchemaType.STRING,
                format: 'date-time',
              },
              status: {
                type: JsonSchemaType.STRING,
              },
              instance_type: {
                type: JsonSchemaType.STRING,
              },
              current_instance_count: {
                type: JsonSchemaType.STRING,
                pattern: '^[0-9]+$',
              },
              endTime: {
                type: JsonSchemaType.STRING,
                format: 'date-time',
              },
              endpoint_status: {
                type: JsonSchemaType.STRING,
              },
              endpoint_name: {
                type: JsonSchemaType.STRING,
              },
              endpoint_type: {
                type: JsonSchemaType.STRING,
              },
              owner_group_or_role: {
                type: JsonSchemaType.ARRAY,
                items: {
                  type: JsonSchemaType.STRING,
                },
              },
              min_instance_number: {
                type: JsonSchemaType.STRING,
                pattern: '^[0-9]+$',
              },
              custom_extensions: {
                type: JsonSchemaType.STRING,
              },
              service_type: {
                type: JsonSchemaType.STRING,
              },
            },
            required: [
              'EndpointDeploymentJobId',
              'autoscaling',
              'max_instance_number',
              'startTime',
              'instance_type',
              'current_instance_count',
              'endpoint_status',
              'endpoint_name',
              'endpoint_type',
              'owner_group_or_role',
              'min_instance_number',
              'custom_extensions',
              'service_type',
            ],
          },
        },
        required: [
          'statusCode',
          'debug',
          'data',
          'message',
        ],
        additionalProperties: false,
      }
      ,
      contentType: 'application/json',
    });
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
        this.executeResultSuccessTopic.topicArn,
        this.executeResultFailTopic.topicArn,
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
        'xray:PutTraceSegments',
        'xray:PutTelemetryRecords',
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
        this.syncTable.tableArn,
        this.instanceMonitorTable.tableArn,
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

    const sqsStatement = new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'sqs:SendMessage',
      ],
      resources: [this.queue.queueArn],
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
    lambdaStartDeployRole.addToPolicy(sqsStatement);
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
        schema: JsonSchemaVersion.DRAFT7,
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
            enum: ['Real-time', 'Async'],
          },
          cool_down_time: {
            type: JsonSchemaType.STRING,
            enum: ['15 minutes', '1 hour', '6 hours', '1 day'],
          },
          service_type: {
            type: JsonSchemaType.STRING,
            enum: ['sd', 'comfy'],
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
        },
        required: [
          'endpoint_type',
          'instance_type',
          'initial_instance_count',
          'autoscaling_enabled',
          'assign_to_roles',
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

  private apiLambda() {
    const role = this.iamRole();
    return new PythonFunction(this.scope, `${this.baseId}-lambda`, {
      entry: '../middleware_api/endpoints',
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'create_endpoint.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: role,
      memorySize: 2048,
      tracing: aws_lambda.Tracing.ACTIVE,
      environment: {
        COMFY_QUEUE_URL: this.queue.queueUrl,
        COMFY_SYNC_TABLE: this.syncTable.tableName,
        COMFY_INSTANCE_MONITOR_TABLE: this.instanceMonitorTable.tableName,
        INFERENCE_ECR_IMAGE_URL: `${this.accountId.toString()}.dkr.ecr.${Aws.REGION}.${Aws.URL_SUFFIX}/esd-inference:${ESD_VERSION}`,
        SNS_INFERENCE_SUCCESS: this.inferenceResultTopic.topicArn,
        SNS_INFERENCE_ERROR: this.inferenceResultErrorTopic.topicArn,
        COMFY_SNS_INFERENCE_SUCCESS: this.executeResultFailTopic.topicArn,
        COMFY_SNS_INFERENCE_ERROR: this.executeResultSuccessTopic.topicArn,
        EXECUTION_ROLE_ARN: role.roleArn,
      },
      layers: [this.layer],
    });
  }


}
