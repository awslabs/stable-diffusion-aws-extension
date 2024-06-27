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
  SCHEMA_MESSAGE, SCHEMA_WORKFLOW_JSON_WORKFLOW
} from "../../shared/schema";
import {ApiValidators} from "../../shared/validator";

export interface UpdateSchemaApiProps {
  router: Resource;
  httpMethod: string;
  workflowsSchemasTable: Table;
  multiUserTable: Table;
  commonLayer: LayerVersion;
}

export class UpdateSchemaApi {
  private readonly router: Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly workflowsSchemasTable: Table;
  private readonly layer: LayerVersion;
  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: UpdateSchemaApiProps) {
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
              operationName: 'UpdateSchema',
              requestValidator: ApiValidators.bodyValidator,
              requestModels: {
                'application/json': this.updateRequestBodyModel(),
              },
              methodResponses: [
                ApiModels.methodResponse(this.responseModel()),
                ApiModels.methodResponses401(),
                ApiModels.methodResponses403(),
              ],
            });
  }

  private updateRequestBodyModel(): Model {
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
          workflow: SCHEMA_WORKFLOW_JSON_WORKFLOW,
        },
        required: [
          'workflow',
        ],
      },
    });
  }

  private responseModel() {
    return new Model(this.scope, `${this.baseId}-resp-model`, {
      restApi: this.router.api,
      modelName: 'UpdateSchemaResponse',
      description: 'Response Model UpdateSchema',
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        title: 'UpdateSchema',
        type: JsonSchemaType.OBJECT,
        properties: {
          statusCode: {
            type: JsonSchemaType.NUMBER,
          },
          debug: SCHEMA_DEBUG,
          message: SCHEMA_MESSAGE,
        },
        required: [
          'statusCode',
          'debug',
          'message',
        ],
      },
      contentType: 'application/json',
    });
  }

  private apiLambda() {
    const role = <Role>Role.fromRoleName(this.scope, `${this.baseId}-role`, `ESDRoleForEndpoint-${Aws.REGION}`);

    return new PythonFunction(
      this.scope,
      `${this.baseId}-lambda`,
      {
        entry: '../middleware_api/schemas',
        architecture: Architecture.X86_64,
        runtime: Runtime.PYTHON_3_10,
        index: 'update_schema.py',
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
