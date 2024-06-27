import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import {Aws, aws_dynamodb, aws_lambda, aws_sqs, Duration} from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model, Resource } from 'aws-cdk-lib/aws-apigateway';
import { Table } from 'aws-cdk-lib/aws-dynamodb';
import { Role } from 'aws-cdk-lib/aws-iam';
import { Architecture, LayerVersion, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Topic } from 'aws-cdk-lib/aws-sns';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import {
  SCHEMA_DEBUG,
  SCHEMA_ENDPOINT_AUTOSCALING,
  SCHEMA_ENDPOINT_CURRENT_INSTANCE_COUNT,
  SCHEMA_ENDPOINT_CUSTOM_EXTENSIONS,
  SCHEMA_ENDPOINT_ID,
  SCHEMA_ENDPOINT_INSTANCE_TYPE,
  SCHEMA_ENDPOINT_MAX_INSTANCE_NUMBER,
  SCHEMA_ENDPOINT_MIN_INSTANCE_NUMBER,
  SCHEMA_ENDPOINT_NAME,
  SCHEMA_ENDPOINT_OWNER_GROUP_OR_ROLE,
  SCHEMA_ENDPOINT_SERVICE_TYPE,
  SCHEMA_ENDPOINT_START_TIME,
  SCHEMA_ENDPOINT_STATUS,
  SCHEMA_ENDPOINT_TYPE,
  SCHEMA_MESSAGE, SCHEMA_WORKFLOW_NAME,
} from '../../shared/schema';
import { ApiValidators } from '../../shared/validator';

export interface CreateEndpointApiProps {
  router: Resource;
  httpMethod: string;
  endpointDeploymentTable: Table;
  multiUserTable: Table;
  syncTable: aws_dynamodb.Table;
  instanceMonitorTable: aws_dynamodb.Table;
  workflowsTable: aws_dynamodb.Table;
  commonLayer: LayerVersion;
  userNotifySNS: Topic;
  inferenceResultTopic: Topic;
  inferenceResultErrorTopic: Topic;
  queue: aws_sqs.Queue;
  executeResultSuccessTopic: Topic;
  executeResultFailTopic: Topic;
}

export class CreateEndpointApi {
  private readonly router: Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly syncTable: Table;
  private readonly instanceMonitorTable: Table;
  private readonly workflowsTable: Table;
  private readonly layer: LayerVersion;
  private readonly baseId: string;
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
    this.syncTable = props.syncTable;
    this.workflowsTable = props.workflowsTable;
    this.instanceMonitorTable = props.instanceMonitorTable;
    this.layer = props.commonLayer;
    this.inferenceResultTopic = props.inferenceResultTopic;
    this.inferenceResultErrorTopic = props.inferenceResultErrorTopic;
    this.executeResultSuccessTopic = props.executeResultSuccessTopic;
    this.executeResultFailTopic = props.executeResultFailTopic;
    this.queue = props.queue;

    const lambdaFunction = this.apiLambda();

    const integration = new LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.addMethod(this.httpMethod, integration, {
      apiKeyRequired: true,
      requestValidator: ApiValidators.bodyValidator,
      requestModels: {
        'application/json': this.createRequestBodyModel(),
      },
      operationName: 'CreateEndpoint',
      methodResponses: [
        ApiModels.methodResponse(this.responseModel(), '202'),
        ApiModels.methodResponses400(),
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
      description: `Response Model ${this.baseId}`,
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
              EndpointDeploymentJobId: SCHEMA_ENDPOINT_ID,
              autoscaling: SCHEMA_ENDPOINT_AUTOSCALING,
              max_instance_number: SCHEMA_ENDPOINT_MAX_INSTANCE_NUMBER,
              startTime: SCHEMA_ENDPOINT_START_TIME,
              instance_type: SCHEMA_ENDPOINT_INSTANCE_TYPE,
              current_instance_count: SCHEMA_ENDPOINT_CURRENT_INSTANCE_COUNT,
              endpoint_status: SCHEMA_ENDPOINT_STATUS,
              endpoint_name: SCHEMA_ENDPOINT_NAME,
              endpoint_type: SCHEMA_ENDPOINT_TYPE,
              service_type: SCHEMA_ENDPOINT_SERVICE_TYPE,
              owner_group_or_role: SCHEMA_ENDPOINT_OWNER_GROUP_OR_ROLE,
              min_instance_number: SCHEMA_ENDPOINT_MIN_INSTANCE_NUMBER,
              custom_extensions: SCHEMA_ENDPOINT_CUSTOM_EXTENSIONS,
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
      }
      ,
      contentType: 'application/json',
    });
  }

  private createRequestBodyModel(): Model {
    return new Model(this.scope, `${this.baseId}-model`, {
      restApi: this.router.api,
      contentType: 'application/json',
      modelName: `${this.baseId}Request`,
      description: `Request Model ${this.baseId}`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        title: this.baseId,
        type: JsonSchemaType.OBJECT,
        properties: {
          endpoint_name: SCHEMA_ENDPOINT_NAME,
          custom_docker_image_uri: {
            type: JsonSchemaType.STRING,
          },
          endpoint_type: SCHEMA_ENDPOINT_TYPE,
          workflow_name: SCHEMA_WORKFLOW_NAME,
          cool_down_time: {
            type: JsonSchemaType.STRING,
            enum: ['15 minutes', '1 hour', '6 hours', '1 day'],
          },
          service_type: {
            type: JsonSchemaType.STRING,
            enum: ['sd', 'comfy'],
          },
          instance_type: SCHEMA_ENDPOINT_INSTANCE_TYPE,
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

  private apiLambda() {
    const role = <Role>Role.fromRoleName(this.scope, `${this.baseId}-role`, `ESDRoleForEndpoint-${Aws.REGION}`);

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
        SNS_INFERENCE_SUCCESS: this.inferenceResultTopic.topicArn,
        SNS_INFERENCE_ERROR: this.inferenceResultErrorTopic.topicArn,
        COMFY_SNS_INFERENCE_SUCCESS: this.executeResultFailTopic.topicArn,
        COMFY_SNS_INFERENCE_ERROR: this.executeResultSuccessTopic.topicArn,
        WORKFLOWS_TABLE: this.workflowsTable.tableName,
        EXECUTION_ROLE_ARN: role.roleArn,
      },
      layers: [this.layer],
    });
  }


}
