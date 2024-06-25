import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, aws_lambda, Duration } from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model, Resource } from 'aws-cdk-lib/aws-apigateway';
import { Table } from 'aws-cdk-lib/aws-dynamodb';
import { Effect, PolicyStatement, Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';
import { Architecture, LayerVersion, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import {
  SCHEMA_DEBUG,
  SCHEMA_MESSAGE,
  SCHEMA_WORKFLOW_JSON_NAME,
  SCHEMA_WORKFLOW_JSON_PAYLOAD_JSON, SCHEMA_WORKFLOW_JSON_STATUS, SCHEMA_WORKFLOW_JSON_WORKFLOW
} from "../../shared/schema";

export interface GetSchemaApiProps {
  router: Resource;
  httpMethod: string;
  workflowsSchemasTable: Table;
  multiUserTable: Table;
  commonLayer: LayerVersion;
}

export class GetSchemaApi {
  private readonly router: Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly workflowsSchemasTable: Table;
  private readonly multiUserTable: Table;
  private readonly layer: LayerVersion;
  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: GetSchemaApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.workflowsSchemasTable = props.workflowsSchemasTable;
    this.layer = props.commonLayer;
    this.multiUserTable = props.multiUserTable;

    const lambdaFunction = this.apiLambda();

    const lambdaIntegration = new LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.addResource('{name}')
        .addMethod(
            this.httpMethod,
            lambdaIntegration,
            {
              apiKeyRequired: true,
              operationName: 'GetSchema',
              methodResponses: [
                ApiModels.methodResponse(this.responseModel()),
                ApiModels.methodResponses401(),
                ApiModels.methodResponses403(),
                ApiModels.methodResponses404(),
              ],
            });
  }

  private responseModel() {
    return new Model(this.scope, `${this.baseId}-resp-model`, {
      restApi: this.router.api,
      modelName: 'GetSchemaResponse',
      description: 'Response Model GetSchema',
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        title: 'GetSchema',
        type: JsonSchemaType.OBJECT,
        properties: {
          statusCode: {
            type: JsonSchemaType.NUMBER,
          },
          debug: SCHEMA_DEBUG,
          message: SCHEMA_MESSAGE,
          data: {
            type: JsonSchemaType.OBJECT,
            properties: {
              name: SCHEMA_WORKFLOW_JSON_NAME,
              payload: SCHEMA_WORKFLOW_JSON_PAYLOAD_JSON,
              status: SCHEMA_WORKFLOW_JSON_STATUS,
              workflow: SCHEMA_WORKFLOW_JSON_WORKFLOW,
            },
            required: [
              'name',
              'payload',
              'status',
              'workflow',
            ],
          },
        },
        required: [
          'statusCode',
          'debug',
          'data',
          'message',
        ],
      },
      contentType: 'application/json',
    });
  }

  private apiLambda() {
    return new PythonFunction(
      this.scope,
      `${this.baseId}-lambda`,
      {
        entry: '../middleware_api/schemas',
        architecture: Architecture.X86_64,
        runtime: Runtime.PYTHON_3_10,
        index: 'get_schema.py',
        handler: 'handler',
        timeout: Duration.seconds(900),
        role: this.iamRole(),
        memorySize: 2048,
        tracing: aws_lambda.Tracing.ACTIVE,
        environment: {
          WORKFLOW_SCHEMA_TABLE: this.workflowsSchemasTable.tableName,
        },
        layers: [this.layer],
      });
  }

  private iamRole(): Role {

    const newRole = new Role(
      this.scope,
      `${this.baseId}-role`,
      {
        assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
      },
    );

    newRole.addToPolicy(new PolicyStatement({
      actions: [
        'dynamodb:GetItem',
        'dynamodb:Query',
        'dynamodb:Scan',
      ],
      resources: [
        this.workflowsSchemasTable.tableArn,
        this.multiUserTable.tableArn,
      ],
    }));

    newRole.addToPolicy(new PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'logs:CreateLogGroup',
        'logs:CreateLogStream',
        'logs:PutLogEvents',
      ],
      resources: [`arn:${Aws.PARTITION}:logs:${Aws.REGION}:${Aws.ACCOUNT_ID}:log-group:*:*`],
    }));

    return newRole;
  }
}
