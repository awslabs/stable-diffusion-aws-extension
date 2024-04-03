import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, aws_apigateway, aws_dynamodb, aws_iam, aws_lambda, aws_s3, Duration } from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model, RequestValidator } from 'aws-cdk-lib/aws-apigateway';
import { Effect, PolicyStatement } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Size } from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import { SCHEMA_DEBUG } from '../../shared/schema';

export interface CreateInferenceJobApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  endpointDeploymentTable: aws_dynamodb.Table;
  inferenceJobTable: aws_dynamodb.Table;
  s3Bucket: aws_s3.Bucket;
  commonLayer: aws_lambda.LayerVersion;
  checkpointTable: aws_dynamodb.Table;
  multiUserTable: aws_dynamodb.Table;
}

export class CreateInferenceJobApi {

  private readonly id: string;
  private readonly scope: Construct;
  private readonly endpointDeploymentTable: aws_dynamodb.Table;
  private readonly inferenceJobTable: aws_dynamodb.Table;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly s3Bucket: aws_s3.Bucket;
  private readonly httpMethod: string;
  private readonly router: aws_apigateway.Resource;
  private readonly checkpointTable: aws_dynamodb.Table;
  private readonly multiUserTable: aws_dynamodb.Table;

  constructor(scope: Construct, id: string, props: CreateInferenceJobApiProps) {
    this.id = id;
    this.scope = scope;
    this.checkpointTable = props.checkpointTable;
    this.multiUserTable = props.multiUserTable;
    this.endpointDeploymentTable = props.endpointDeploymentTable;
    this.inferenceJobTable = props.inferenceJobTable;
    this.layer = props.commonLayer;
    this.s3Bucket = props.s3Bucket;
    this.httpMethod = props.httpMethod;
    this.router = props.router;

    const lambdaFunction = this.apiLambda();

    const lambdaIntegration = new LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.addMethod(this.httpMethod, lambdaIntegration, {
      apiKeyRequired: true,
      requestValidator: this.createRequestValidator(),
      requestModels: {
        'application/json': this.createModel(),
      },
      operationName: 'CreateInferenceJob',
      methodResponses: [
        ApiModels.methodResponse(this.responseModel(), '201'),
        ApiModels.methodResponses401(),
        ApiModels.methodResponses403(),
        ApiModels.methodResponses404(),
      ],
    });
  }

  private responseModel() {
    return new Model(this.scope, `${this.id}-resp-model`, {
      restApi: this.router.api,
      modelName: 'CreateInferenceJobResponse',
      description: 'CreateInferenceJob Response Model',
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        title: this.id,
        type: JsonSchemaType.OBJECT,
        properties: {
          statusCode: {
            type: JsonSchemaType.NUMBER,
          },
          debug: SCHEMA_DEBUG,
          data: {
            type: JsonSchemaType.OBJECT,
            properties: {
              inference: {
                type: JsonSchemaType.OBJECT,
                properties: {
                  id: {
                    type: JsonSchemaType.STRING,
                    format: 'uuid',
                  },
                  type: {
                    type: JsonSchemaType.STRING,
                  },
                  api_params_s3_location: {
                    type: JsonSchemaType.STRING,
                    format: 'uri',
                  },
                  api_params_s3_upload_url: {
                    type: JsonSchemaType.STRING,
                    format: 'uri',
                  },
                  models: {
                    type: JsonSchemaType.ARRAY,
                    items: {
                      type: JsonSchemaType.OBJECT,
                      properties: {
                        id: {
                          type: JsonSchemaType.STRING,
                          format: 'uuid',
                        },
                        name: {
                          type: JsonSchemaType.ARRAY,
                          items: {
                            type: JsonSchemaType.STRING,
                          },
                        },
                        type: {
                          type: JsonSchemaType.STRING,
                        },
                      },
                      required: [
                        'id',
                        'name',
                        'type',
                      ],
                      additionalProperties: false,
                    },
                  },
                },
                required: [
                  'id',
                  'type',
                  'api_params_s3_location',
                  'api_params_s3_upload_url',
                  'models',
                ],
                additionalProperties: false,
              },
            },
            required: [
              'inference',
            ],
            additionalProperties: false,
          },
          message: {
            type: JsonSchemaType.STRING,
          },
        },
        required: [
          'statusCode',
          'debug',
          'data',
          'message',
        ],
        additionalProperties: false,
      },
      contentType: 'application/json',
    });
  }

  private createModel(): Model {
    return new Model(this.scope, `${this.id}-model`, {
      restApi: this.router.api,
      modelName: this.id,
      description: `${this.id} Request Model`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        title: this.id,
        type: JsonSchemaType.OBJECT,
        properties: {
          task_type: {
            type: JsonSchemaType.STRING,
            minLength: 1,
          },
          custom_extensions: {
            type: JsonSchemaType.STRING,
          },
          inference_type: {
            type: JsonSchemaType.STRING,
            enum: ['Real-time', 'Async'],
          },
          payload_string: {
            type: JsonSchemaType.STRING,
          },
          models: {
            type: JsonSchemaType.OBJECT,
            properties: {
              embeddings: {
                type: JsonSchemaType.ARRAY,
              },
            },
          },
        },
        required: [
          'task_type',
          'inference_type',
          'models',
        ],
      },
      contentType: 'application/json',
    });
  }

  private lambdaRole(): aws_iam.Role {
    const newRole = new aws_iam.Role(this.scope, `${this.id}-role`, {
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
      ],
      resources: [
        this.inferenceJobTable.tableArn,
        this.endpointDeploymentTable.tableArn,
        this.checkpointTable.tableArn,
        this.multiUserTable.tableArn,
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

    newRole.addToPolicy(new PolicyStatement({
      actions: [
        's3:PutObject',
      ],
      resources: [
        `${this.s3Bucket.bucketArn}/*`,
        `arn:${Aws.PARTITION}:s3:::*SageMaker*`,
      ],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        's3:GetObject',
        's3:PutObject',
        's3:DeleteObject',
        's3:ListBucket',
      ],
      resources: [`${this.s3Bucket.bucketArn}/*`,
        `arn:${Aws.PARTITION}:s3:::*sagemaker*`],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'logs:CreateLogGroup',
        'logs:CreateLogStream',
        'logs:PutLogEvents',
        'kms:Decrypt',
      ],
      resources: ['*'],
    }));

    return newRole;
  }

  private createRequestValidator(): RequestValidator {
    return new RequestValidator(
      this.scope,
      `${this.id}-create-infer-Validator`,
      {
        restApi: this.router.api,
        validateRequestBody: true,
      });
  }

  private apiLambda() {
    return new PythonFunction(this.scope, `${this.id}-lambda`, {
      entry: '../middleware_api/inferences',
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'create_inference_job.py',
      handler: 'handler',
      memorySize: 3070,
      tracing: aws_lambda.Tracing.ACTIVE,
      ephemeralStorageSize: Size.gibibytes(10),
      timeout: Duration.seconds(900),
      role: this.lambdaRole(),
      environment: {
        INFERENCE_JOB_TABLE: this.inferenceJobTable.tableName,
        CHECKPOINT_TABLE: this.checkpointTable.tableName,
      },
      layers: [this.layer],
    });
  }

}
