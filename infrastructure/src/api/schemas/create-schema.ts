import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import {aws_lambda, Duration} from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model, Resource } from 'aws-cdk-lib/aws-apigateway';
import { Table } from 'aws-cdk-lib/aws-dynamodb';
import { Role } from 'aws-cdk-lib/aws-iam';
import { Architecture, LayerVersion, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import { ApiValidators } from '../../shared/validator';
import {
  SCHEMA_DEBUG,
  SCHEMA_MESSAGE, SCHEMA_WORKFLOW_JSON_CREATED, SCHEMA_WORKFLOW_JSON_NAME,
  SCHEMA_WORKFLOW_JSON_PAYLOAD_JSON, SCHEMA_WORKFLOW_JSON_WORKFLOW
} from "../../shared/schema";
import {ESD_ROLE} from "../../shared/const";

export interface CreateSchemaApiProps {
  router: Resource;
  httpMethod: string;
  workflowsSchemasTable: Table;
  multiUserTable: Table;
  commonLayer: LayerVersion;
}

export class CreateSchemaApi {
  private readonly router: Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly workflowsSchemasTable: Table;
  private readonly layer: LayerVersion;
  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: CreateSchemaApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.workflowsSchemasTable = props.workflowsSchemasTable;
    this.layer = props.commonLayer;

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
      operationName: 'CreateSchema',
      methodResponses: [
        ApiModels.methodResponse(this.responseModel()),
        ApiModels.methodResponses400(),
        ApiModels.methodResponses401(),
        ApiModels.methodResponses403(),
      ],
    });
  }

  private responseModel() {
    return new Model(this.scope, `${this.baseId}-resp-model`, {
      restApi: this.router.api,
      modelName: 'CreateSchemaResponse',
      description: `Response Model ${this.baseId}`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        type: JsonSchemaType.OBJECT,
        title: 'CreateSchemaResponse',
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
          name: SCHEMA_WORKFLOW_JSON_NAME,
          payload: SCHEMA_WORKFLOW_JSON_PAYLOAD_JSON,
          workflow: SCHEMA_WORKFLOW_JSON_WORKFLOW,
        },
        required: [
          'name',
          'payload',
          'workflow',
        ],
      },
    });
  }

  private apiLambda() {
    const role = <Role>Role.fromRoleName(this.scope, `${this.baseId}-role`, ESD_ROLE);

    return new PythonFunction(this.scope, `${this.baseId}-lambda`, {
      entry: '../middleware_api/schemas',
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'create_schema.py',
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
