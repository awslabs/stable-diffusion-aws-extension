import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, aws_apigateway, aws_dynamodb, aws_iam, aws_lambda, aws_s3, Duration } from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model } from 'aws-cdk-lib/aws-apigateway';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Size } from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import { SCHEMA_CHECKPOINT_ID, SCHEMA_CHECKPOINT_STATUS, SCHEMA_CHECKPOINT_TYPE, SCHEMA_DEBUG, SCHEMA_MESSAGE } from '../../shared/schema';
import { ApiValidators } from '../../shared/validator';


export interface UpdateCheckPointApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  checkpointTable: aws_dynamodb.Table;
  userTable: aws_dynamodb.Table;
  commonLayer: aws_lambda.LayerVersion;
  s3Bucket: aws_s3.Bucket;
}

export class UpdateCheckPointApi {
  public router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly checkpointTable: aws_dynamodb.Table;
  private readonly userTable: aws_dynamodb.Table;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly s3Bucket: aws_s3.Bucket;
  private readonly role: aws_iam.Role;
  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: UpdateCheckPointApiProps) {
    this.scope = scope;
    this.layer = props.commonLayer;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.checkpointTable = props.checkpointTable;
    this.userTable = props.userTable;
    this.s3Bucket = props.s3Bucket;
    this.role = this.iamRole();

    const renameLambdaFunction = this.apiRenameLambda();

    const lambdaFunction = this.apiLambda(renameLambdaFunction);

    const lambdaIntegration = new LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.addResource('{id}')
      .addMethod(this.httpMethod, lambdaIntegration,
        {
          apiKeyRequired: true,
          requestValidator: ApiValidators.validator,
          requestModels: {
            'application/json': this.createRequestBodyModel(),
          },
          operationName: 'UpdateCheckpoint',
          methodResponses: [
            ApiModels.methodResponse(this.responseUpdateModel(), '200'),
            ApiModels.methodResponse(this.responseRenameModel(), '202'),
            ApiModels.methodResponses400(),
            ApiModels.methodResponses401(),
            ApiModels.methodResponses403(),
            ApiModels.methodResponses504(),
          ],
        });
  }

  private responseRenameModel() {
    return new Model(this.scope, `${this.baseId}-rename-model`, {
      restApi: this.router.api,
      modelName: 'UpdateCheckpointNameResponse',
      description: `Response Model ${this.baseId}`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        type: JsonSchemaType.OBJECT,
        properties: {
          statusCode: {
            type: JsonSchemaType.NUMBER,
            description: 'The HTTP status code of the response.',
          },
          debug: SCHEMA_DEBUG,
          message: SCHEMA_MESSAGE,
        },
        required: [
          'statusCode',
          'debug',
          'message',
        ],
      }
      ,
      contentType: 'application/json',
    });
  }

  private responseUpdateModel() {
    return new Model(this.scope, `${this.baseId}-update-model`, {
      restApi: this.router.api,
      modelName: 'UpdateCheckpointResponse',
      description: `Response Model ${this.baseId}`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        type: JsonSchemaType.OBJECT,
        title: 'UpdateCheckpointResponse',
        properties: {
          statusCode: {
            type: JsonSchemaType.NUMBER,
          },
          debug: SCHEMA_DEBUG,
          message: SCHEMA_MESSAGE,
          data: {
            type: JsonSchemaType.OBJECT,
            properties: {
              checkpoint: {
                type: JsonSchemaType.OBJECT,
                properties: {
                  id: SCHEMA_CHECKPOINT_ID,
                  type: SCHEMA_CHECKPOINT_TYPE,
                  s3_location: {
                    type: JsonSchemaType.STRING,
                    format: 'uri',
                  },
                  status: SCHEMA_CHECKPOINT_STATUS,
                  params: {
                    type: JsonSchemaType.OBJECT,
                    properties: {
                      creator: {
                        type: JsonSchemaType.STRING,
                      },
                      multipart_upload: {
                        type: JsonSchemaType.OBJECT,
                        patternProperties: {
                          '.*': {
                            type: JsonSchemaType.OBJECT,
                            properties: {
                              bucket: {
                                type: JsonSchemaType.STRING,
                              },
                              upload_id: {
                                type: JsonSchemaType.STRING,
                              },
                              key: {
                                type: JsonSchemaType.STRING,
                              },
                            },
                            required: [
                              'bucket',
                              'upload_id',
                              'key',
                            ],
                          },
                        },
                      },
                      message: {
                        type: JsonSchemaType.STRING,
                      },
                      created: {
                        type: JsonSchemaType.STRING,
                        format: 'date-time',
                      },
                    },
                    required: [
                      'creator',
                      'multipart_upload',
                      'message',
                      'created',
                    ],
                  },
                },
                required: [
                  'id',
                  'type',
                  's3_location',
                  'status',
                  'params',
                ],
              },
            },
            required: [
              'checkpoint',
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
    const newRole = new aws_iam.Role(this.scope, `${this.baseId}-update-role`, {
      assumedBy: new aws_iam.ServicePrincipal('lambda.amazonaws.com'),
    });

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'dynamodb:BatchGetItem',
        'dynamodb:GetItem',
        'dynamodb:Scan',
        'dynamodb:Query',
        'dynamodb:UpdateItem',
      ],
      resources: [
        this.userTable.tableArn,
        this.checkpointTable.tableArn,
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
        's3:CopyObject',
        's3:DeleteObject',
      ],
      resources: [
        `${this.s3Bucket.bucketArn}/*`,
      ],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        's3:GetObject',
        's3:PutObject',
        's3:DeleteObject',
        's3:ListBucket',
        's3:CopyObject',
        's3:AbortMultipartUpload',
        's3:ListMultipartUploadParts',
        's3:ListBucketMultipartUploads',
      ],
      resources: [`${this.s3Bucket.bucketArn}/*`,
        `arn:${Aws.PARTITION}:s3:::*SageMaker*`],
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
          status: SCHEMA_CHECKPOINT_STATUS,
          name: {
            type: JsonSchemaType.STRING,
            minLength: 1,
            maxLength: 20,
            pattern: '^[A-Za-z][A-Za-z0-9_-]*$',
          },
          multi_parts_tags: {
            type: JsonSchemaType.OBJECT,
          },
        },
      },
      contentType: 'application/json',
    });
  }

  private apiRenameLambda() {
    return new PythonFunction(this.scope, `${this.baseId}-rename-lambda`, {
      entry: '../middleware_api/checkpoints',
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'update_checkpoint_rename.py',
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

  private apiLambda(renameLambdaFunction: PythonFunction) {
    return new PythonFunction(this.scope, `${this.baseId}-lambda`, {
      entry: '../middleware_api/checkpoints',
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'update_checkpoint.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.role,
      memorySize: 3070,
      tracing: aws_lambda.Tracing.ACTIVE,
      environment: {
        CHECKPOINT_TABLE: this.checkpointTable.tableName,
        RENAME_LAMBDA_NAME: renameLambdaFunction.functionName,
      },
      layers: [this.layer],
    });
  }

}

