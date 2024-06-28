import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import {aws_lambda, Duration} from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model, Resource } from 'aws-cdk-lib/aws-apigateway';
import { Table } from 'aws-cdk-lib/aws-dynamodb';
import { Role } from 'aws-cdk-lib/aws-iam';
import { Architecture, LayerVersion, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import {
  SCHEMA_DEBUG,
  SCHEMA_MESSAGE,
  SCHEMA_WORKFLOW_IMAGE_URI,
  SCHEMA_WORKFLOW_NAME,
  SCHEMA_WORKFLOW_PAYLOAD_JSON,
  SCHEMA_WORKFLOW_SIZE,
  SCHEMA_WORKFLOW_STATUS,
} from '../../shared/schema';
import { ApiValidators } from '../../shared/validator';
import {ESD_ROLE} from "../../shared/const";

export interface CreateWorkflowApiProps {
  router: Resource;
  httpMethod: string;
  workflowsTable: Table;
  multiUserTable: Table;
  commonLayer: LayerVersion;
}

export class CreateWorkflowApi {
  private readonly router: Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly workflowsTable: Table;
  private readonly layer: LayerVersion;
  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: CreateWorkflowApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.workflowsTable = props.workflowsTable;
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
      operationName: 'CreateWorkflow',
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
      modelName: 'CreateWorkflowResponse',
      description: `Response Model ${this.baseId}`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        type: JsonSchemaType.OBJECT,
        title: 'CreateWorkflowResponse',
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
              name: SCHEMA_WORKFLOW_NAME,
              size: SCHEMA_WORKFLOW_SIZE,
              status: SCHEMA_WORKFLOW_STATUS,
              image_uri: SCHEMA_WORKFLOW_IMAGE_URI,
              payload_json: SCHEMA_WORKFLOW_PAYLOAD_JSON,
            },
            required: [
              'name',
              'size',
              'status',
              'image_uri',
              'payload_json',
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
          name: SCHEMA_WORKFLOW_NAME,
          size: SCHEMA_WORKFLOW_SIZE,
          image_uri: SCHEMA_WORKFLOW_IMAGE_URI,
          payload_json: SCHEMA_WORKFLOW_PAYLOAD_JSON,
        },
        required: [
          'name',
          'size',
          'image_uri',
          'payload_json',
        ],
      },
    });
  }

  private apiLambda() {
    const role = <Role>Role.fromRoleName(this.scope, `${this.baseId}-role`, ESD_ROLE);

    return new PythonFunction(this.scope, `${this.baseId}-lambda`, {
      entry: '../middleware_api/workflows',
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'create_workflow.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: role,
      memorySize: 2048,
      tracing: aws_lambda.Tracing.ACTIVE,
      environment: {
        WORKFLOWS_TABLE: this.workflowsTable.tableName,
      },
      layers: [this.layer],
    });
  }


}
