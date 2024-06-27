import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import {Aws, aws_lambda, Duration} from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model, Resource } from 'aws-cdk-lib/aws-apigateway';
import { Table } from 'aws-cdk-lib/aws-dynamodb';
import { Role } from 'aws-cdk-lib/aws-iam';
import { Architecture, LayerVersion, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import {
  SCHEMA_DEBUG,
  SCHEMA_MESSAGE, SCHEMA_WORKFLOW_JSON_CREATED,
  SCHEMA_WORKFLOW_JSON_NAME,
  SCHEMA_WORKFLOW_JSON_PAYLOAD_JSON, SCHEMA_WORKFLOW_JSON_WORKFLOW
} from "../../shared/schema";
import {ESD_ROLE} from "../../shared/const";

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
  private readonly layer: LayerVersion;
  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: GetSchemaApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.workflowsSchemasTable = props.workflowsSchemasTable;
    this.layer = props.commonLayer;

    const lambdaFunction = this.apiLambda();

    const lambdaIntegration = new LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.addMethod(
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
              workflow: SCHEMA_WORKFLOW_JSON_WORKFLOW,
              create_time: SCHEMA_WORKFLOW_JSON_CREATED,
            },
            required: [
              'name',
              'payload',
              'workflow',
              'create_time',
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
    const role = <Role>Role.fromRoleName(this.scope, `${this.baseId}-role`, `${ESD_ROLE}-${Aws.REGION}`);

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
        role: role,
        memorySize: 2048,
        tracing: aws_lambda.Tracing.ACTIVE,
        environment: {
          WORKFLOW_SCHEMA_TABLE: this.workflowsSchemasTable.tableName,
        },
        layers: [this.layer],
      });
  }

}
