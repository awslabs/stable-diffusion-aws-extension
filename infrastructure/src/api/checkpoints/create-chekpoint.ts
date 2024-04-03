import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, aws_apigateway, aws_dynamodb, aws_iam, aws_lambda, aws_s3, Duration } from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, Model, RequestValidator } from 'aws-cdk-lib/aws-apigateway';
import { MethodOptions } from 'aws-cdk-lib/aws-apigateway/lib/method';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Size } from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import { SCHEMA_DEBUG } from '../../shared/schema';


export interface CreateCheckPointApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  checkpointTable: aws_dynamodb.Table;
  multiUserTable: aws_dynamodb.Table;
  commonLayer: aws_lambda.LayerVersion;
  s3Bucket: aws_s3.Bucket;
}

export class CreateCheckPointApi {
  public requestValidator: RequestValidator;
  public lambdaIntegration: aws_apigateway.LambdaIntegration;
  public router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly checkpointTable: aws_dynamodb.Table;
  private readonly multiUserTable: aws_dynamodb.Table;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly s3Bucket: aws_s3.Bucket;
  private readonly uploadByUrlLambda: PythonFunction;
  private readonly role: aws_iam.Role;
  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: CreateCheckPointApiProps) {
    this.scope = scope;
    this.httpMethod = props.httpMethod;
    this.checkpointTable = props.checkpointTable;
    this.multiUserTable = props.multiUserTable;
    this.baseId = id;
    this.router = props.router;
    this.layer = props.commonLayer;
    this.s3Bucket = props.s3Bucket;
    this.role = this.iamRole();
    this.requestValidator = this.createRequestValidator();
    this.uploadByUrlLambda = this.uploadByUrlLambdaFunction();

    const lambdaFunction = this.apiLambda();

    this.lambdaIntegration = new aws_apigateway.LambdaIntegration(lambdaFunction, { proxy: true });

    this.router.addMethod(this.httpMethod, this.lambdaIntegration, <MethodOptions>{
      apiKeyRequired: true,
      requestValidator: this.requestValidator,
      requestModels: {
        'application/json': this.createRequestModel(),
      },
      operationName: 'CreateCheckpoint',
      methodResponses: [
        ApiModels.methodResponse(this.responseModel(), '201'),
        ApiModels.methodResponse(this.responseUrlModel(), '202'),
        ApiModels.methodResponses400(),
        ApiModels.methodResponses401(),
        ApiModels.methodResponses403(),
        ApiModels.methodResponses504(),
      ],
    });
  }

  private responseUrlModel() {
    return new Model(this.scope, `${this.baseId}-url-model`, {
      restApi: this.router.api,
      modelName: 'CreateCheckpointUrlResponse',
      description: `${this.baseId} Response Model`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        type: JsonSchemaType.OBJECT,
        properties: {
          statusCode: {
            type: JsonSchemaType.INTEGER,
          },
          debug: SCHEMA_DEBUG,
          message: {
            type: JsonSchemaType.STRING,
          },
        },
        required: [
          'debug',
          'message',
          'statusCode',
        ],
        additionalProperties: false,
      },
      contentType: 'application/json',
    });
  }

  private responseModel() {
    return new Model(this.scope, `${this.baseId}-update-model`, {
      restApi: this.router.api,
      modelName: 'CreateCheckpointResponse',
      description: `${this.baseId} Response Model`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        type: JsonSchemaType.OBJECT,
        properties: {
          statusCode: {
            type: JsonSchemaType.INTEGER,
          },
          debug: SCHEMA_DEBUG,
          data: {
            type: JsonSchemaType.OBJECT,
            properties: {
              checkpoint: {
                type: JsonSchemaType.OBJECT,
                properties: {
                  id: {
                    type: JsonSchemaType.STRING,
                  },
                  type: {
                    type: JsonSchemaType.STRING,
                  },
                  s3_location: {
                    type: JsonSchemaType.STRING,
                  },
                  status: {
                    type: JsonSchemaType.STRING,
                  },
                  params: {
                    type: JsonSchemaType.OBJECT,
                    properties: {
                      message: {
                        type: JsonSchemaType.STRING,
                      },
                      creator: {
                        type: JsonSchemaType.STRING,
                      },
                      created: {
                        type: JsonSchemaType.STRING,
                      },
                      multipart_upload: {
                        type: JsonSchemaType.OBJECT,
                        properties: {
                          '.*': {
                            type: JsonSchemaType.OBJECT,
                            properties: {
                              upload_id: {
                                type: JsonSchemaType.STRING,
                              },
                              bucket: {
                                type: JsonSchemaType.STRING,
                              },
                              key: {
                                type: JsonSchemaType.STRING,
                              },
                            },
                            required: [
                              'bucket',
                              'key',
                              'upload_id',
                            ],
                          },
                        },
                      },
                    },
                    required: [
                      'created',
                      'creator',
                      'message',
                      'multipart_upload',
                    ],
                  },
                },
                required: [
                  'id',
                  'params',
                  's3_location',
                  'status',
                  'type',
                ],
              },
              s3PresignUrl: {
                type: JsonSchemaType.OBJECT,
                properties: {
                  '.*': {
                    type: JsonSchemaType.ARRAY,
                    items: {
                      type: JsonSchemaType.STRING,
                    },
                  },
                },
              },
            },
            required: [
              'checkpoint',
              's3PresignUrl',
            ],
          },
          message: {
            type: JsonSchemaType.STRING,
          },
        },
        required: [
          'data',
          'debug',
          'message',
          'statusCode',
        ],
      }
      ,
      contentType: 'application/json',
    });
  }

  private apiLambda() {
    return new PythonFunction(this.scope, `${this.baseId}-lambda`, {
      entry: '../middleware_api/checkpoints',
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'create_checkpoint.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.role,
      memorySize: 3070,
      tracing: aws_lambda.Tracing.ACTIVE,
      environment: {
        CHECKPOINT_TABLE: this.checkpointTable.tableName,
        UPLOAD_BY_URL_LAMBDA_NAME: this.uploadByUrlLambda.functionName,
      },
      layers: [this.layer],
    });
  }

  private uploadByUrlLambdaFunction() {
    return new PythonFunction(this.scope, `${this.baseId}-url-lambda`, {
      functionName: `${this.baseId}-create-checkpoint-by-url`,
      entry: '../middleware_api/checkpoints',
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'update_checkpoint_by_url.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.role,
      memorySize: 3070,
      tracing: aws_lambda.Tracing.ACTIVE,
      ephemeralStorageSize: Size.mebibytes(10240),
      environment: {
        CHECKPOINT_TABLE: this.checkpointTable.tableName,
      },
      layers: [this.layer],
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
      ],
      resources: [this.checkpointTable.tableArn, this.multiUserTable.tableArn],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        's3:GetObject',
        's3:PutObject',
        's3:DeleteObject',
        's3:ListBucket',
        's3:AbortMultipartUpload',
        's3:ListMultipartUploadParts',
        's3:ListBucketMultipartUploads',
      ],
      resources: [
        `${this.s3Bucket.bucketArn}/*`,
        `arn:${Aws.PARTITION}:s3:::*SageMaker*`,
      ],
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

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'lambda:invokeFunction',
      ],
      resources: [
        `arn:${Aws.PARTITION}:lambda:${Aws.REGION}:${Aws.ACCOUNT_ID}:function:*${this.baseId}*`,
      ],
    }));

    return newRole;
  }

  private createRequestModel(): Model {
    return new Model(this.scope, `${this.baseId}-model`, {
      restApi: this.router.api,
      modelName: `${this.baseId}Request`,
      description: `${this.baseId} Request Model`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        title: this.baseId,
        type: JsonSchemaType.OBJECT,
        properties: {
          checkpoint_type: {
            type: JsonSchemaType.STRING,
            description: 'Type of checkpoint',
            enum: [
              'Stable-diffusion',
              'embeddings',
              'Lora',
              'hypernetworks',
              'ControlNet',
              'VAE',
            ],
          },
          filenames: {
            type: JsonSchemaType.ARRAY,
            items: {
              type: JsonSchemaType.OBJECT,
              properties: {
                filename: {
                  type: JsonSchemaType.STRING,
                  minLength: 1,
                },
                parts_number: {
                  type: JsonSchemaType.INTEGER,
                  minimum: 1,
                  maximum: 100,
                },
              },
            },
            minItems: 1,
            maxItems: 20,
          },
          urls: {
            type: JsonSchemaType.ARRAY,
            items: {
              type: JsonSchemaType.STRING,
              minLength: 1,
            },
            minItems: 1,
            maxItems: 20,
          },
          params: {
            type: JsonSchemaType.OBJECT,
            properties: {
              message: {
                type: JsonSchemaType.STRING,
              },
              creator: {
                type: JsonSchemaType.STRING,
              },
            },
          },
        },
        required: [
          'checkpoint_type',
        ],
      },
      contentType: 'application/json',
    });
  }

  private createRequestValidator(): RequestValidator {
    return new RequestValidator(
      this.scope,
      `${this.baseId}-create-ckpt-validator`,
      {
        restApi: this.router.api,
        validateRequestBody: true,
      });
  }

}

