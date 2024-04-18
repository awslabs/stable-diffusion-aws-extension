import { PythonFunction, PythonFunctionProps } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, aws_apigateway, aws_dynamodb, aws_iam, aws_lambda, Duration } from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model } from 'aws-cdk-lib/aws-apigateway';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Size } from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import {
  SCHEMA_DEBUG,
  SCHEMA_ENDPOINT_NAME,
  SCHEMA_EXECUTE_NEED_SYNC,
  SCHEMA_EXECUTE_PROMPT_ID,
  SCHEMA_INFER_TYPE,
  SCHEMA_MESSAGE,
} from '../../shared/schema';
import { ApiValidators } from '../../shared/validator';


export interface ExecuteApiProps {
  httpMethod: string;
  router: aws_apigateway.Resource;
  configTable: aws_dynamodb.Table;
  executeTable: aws_dynamodb.Table;
  endpointTable: aws_dynamodb.Table;
  commonLayer: aws_lambda.LayerVersion;
}

export class ExecuteApi {
  private readonly baseId: string;
  private readonly router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly configTable: aws_dynamodb.Table;
  private readonly executeTable: aws_dynamodb.Table;
  private readonly endpointTable: aws_dynamodb.Table;

  constructor(scope: Construct, id: string, props: ExecuteApiProps) {
    this.scope = scope;
    this.httpMethod = props.httpMethod;
    this.baseId = id;
    this.router = props.router;
    this.configTable = props.configTable;
    this.executeTable = props.executeTable;
    this.endpointTable = props.endpointTable;
    this.layer = props.commonLayer;

    const lambdaFunction = this.apiLambda();

    const lambdaIntegration = new LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.addMethod(this.httpMethod, lambdaIntegration, {
      apiKeyRequired: true,
      requestValidator: ApiValidators.bodyValidator,
      requestModels: {
        'application/json': this.createRequestBodyModel(),
      },
      operationName: 'CreateExecute',
      methodResponses: [
        ApiModels.methodResponse(this.responseModel(), '201'),
        ApiModels.methodResponses400(),
        ApiModels.methodResponses401(),
        ApiModels.methodResponses403(),
      ],
    });
  }

  private responseModel() {
    return new Model(this.scope, `${this.baseId}-resp-model`, {
      restApi: this.router.api,
      modelName: 'CreateExecuteResponse',
      description: `Response Model ${this.baseId}`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        type: JsonSchemaType.OBJECT,
        title: 'CreateExecuteResponse',
        properties: {
          statusCode: {
            type: JsonSchemaType.INTEGER,
            enum: [
              201,
            ],
          },
          debug: SCHEMA_DEBUG,
          message: SCHEMA_MESSAGE,
          data: {
            type: JsonSchemaType.OBJECT,
            properties: {
              prompt_id: {
                type: JsonSchemaType.STRING,
              },
              endpoint_name: SCHEMA_ENDPOINT_NAME,
              inference_type: SCHEMA_INFER_TYPE,
              need_sync: {
                type: JsonSchemaType.BOOLEAN,
              },
              status: {
                type: JsonSchemaType.STRING,
              },
              number: {
                type: JsonSchemaType.INTEGER,
              },
              front: {
                type: JsonSchemaType.STRING,
              },
              extra_data: {
                type: JsonSchemaType.OBJECT,
                additionalProperties: true,
              },
              client_id: {
                type: JsonSchemaType.STRING,
              },
              instance_id: {
                type: JsonSchemaType.STRING,
              },
              prompt_path: {
                type: JsonSchemaType.STRING,
              },
              create_time: {
                type: JsonSchemaType.STRING,
                format: 'date-time',
              },
              start_time: {
                type: JsonSchemaType.STRING,
                format: 'date-time',
              },
              output_path: {
                type: JsonSchemaType.STRING,
              },
              output_files: {
                type: JsonSchemaType.ARRAY,
                items: {
                  type: JsonSchemaType.STRING,
                },
              },
              temp_path: {
                type: JsonSchemaType.STRING,
              },
              temp_files: {
                type: JsonSchemaType.ARRAY,
                items: {
                  type: JsonSchemaType.OBJECT,
                },
              },
            },
            required: [
              'prompt_id',
              'endpoint_name',
              'inference_type',
              'need_sync',
              'status',
              'create_time',
              'start_time',
              'output_path',
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

  private iamRole(): aws_iam.Role {
    const newRole = new aws_iam.Role(this.scope, `${this.baseId}-role`, {
      assumedBy: new aws_iam.ServicePrincipal('lambda.amazonaws.com'),
    });
    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'dynamodb:BatchGetItem',
        'dynamodb:GetItem',
        'dynamodb:Scan',
        'dynamodb:Query',
        'dynamodb:BatchWriteItem',
        'dynamodb:PutItem',
        'dynamodb:UpdateItem',
        'dynamodb:DeleteItem',
        'dynamodb:Query',
      ],
      resources: [
        this.configTable.tableArn,
        this.executeTable.tableArn,
        `${this.endpointTable.tableArn}`,
        `${this.endpointTable.tableArn}/*`,
      ],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'sagemaker:InvokeEndpointAsync',
        'sagemaker:InvokeEndpoint',
      ],
      resources: [`arn:${Aws.PARTITION}:sagemaker:${Aws.REGION}:${Aws.ACCOUNT_ID}:endpoint/*`],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        's3:GetObject',
        's3:PutObject',
        's3:DeleteObject',
        's3:ListBucket',
        's3:CreateBucket',
      ],
      resources: [
        '*',
      ],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'logs:CreateLogGroup',
        'logs:CreateLogStream',
        'logs:PutLogEvents',
      ],
      resources: ['*'],
    }));
    return newRole;
  }

  private apiLambda() {
    return new PythonFunction(this.scope, `${this.baseId}-lambda`, <PythonFunctionProps>{
      entry: '../middleware_api/comfy',
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'execute.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.iamRole(),
      memorySize: 3070,
      tracing: aws_lambda.Tracing.ACTIVE,
      ephemeralStorageSize: Size.gibibytes(10),
      environment: {
        EXECUTE_TABLE: this.executeTable.tableName,
        CONFIG_TABLE: this.configTable.tableName,
      },
      layers: [this.layer],
    });
  }

  private createRequestBodyModel(): Model {
    return new Model(this.scope, `${this.baseId}-model`, {
      restApi: this.router.api,
      modelName: this.baseId,
      description: `Request Model ${this.baseId}`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        title: this.baseId,
        type: JsonSchemaType.OBJECT,
        properties: {
          prompt_id: SCHEMA_EXECUTE_PROMPT_ID,
          prompt: {
            type: JsonSchemaType.OBJECT,
            minItems: 1,
            additionalProperties: true,
          },
          endpoint_name: SCHEMA_ENDPOINT_NAME,
          need_sync: SCHEMA_EXECUTE_NEED_SYNC,
          number: {
            type: JsonSchemaType.STRING,
            minLength: 1,
          },
          front: {
            type: JsonSchemaType.BOOLEAN,
            minLength: 1,
          },
          extra_data: {
            type: JsonSchemaType.OBJECT,
            minLength: 1,
            additionalProperties: true,
          },
          client_id: {
            type: JsonSchemaType.STRING,
            minLength: 1,
          },
          need_prepare: {
            type: JsonSchemaType.BOOLEAN,
            minLength: 1,
          },
          prepare_props: {
            type: JsonSchemaType.OBJECT,
            minItems: 1,
            additionalProperties: true,
          },
        },
        required: [
          'prompt_id',
          'prompt',
          'need_sync',
          'endpoint_name',
        ],
      },
      contentType: 'application/json',
    });
  }

}

