import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { aws_apigateway, aws_dynamodb, aws_iam, aws_lambda, Duration } from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, Model } from 'aws-cdk-lib/aws-apigateway';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import { SCHEMA_DEBUG } from '../../shared/schema';


export interface ListCheckPointsApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  checkpointTable: aws_dynamodb.Table;
  multiUserTable: aws_dynamodb.Table;
  commonLayer: aws_lambda.LayerVersion;
}

export class ListCheckPointsApi {
  public lambdaIntegration: aws_apigateway.LambdaIntegration;
  public router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly checkpointTable: aws_dynamodb.Table;
  private readonly multiUserTable: aws_dynamodb.Table;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: ListCheckPointsApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.checkpointTable = props.checkpointTable;
    this.multiUserTable = props.multiUserTable;
    this.layer = props.commonLayer;

    const lambdaFunction = this.apiLambda();

    this.lambdaIntegration = new aws_apigateway.LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.addMethod(this.httpMethod, this.lambdaIntegration, {
      apiKeyRequired: true,
      operationName: 'ListCheckpoints',
      methodResponses: [
        ApiModels.methodResponse(this.responseModel(), '200'),
        ApiModels.methodResponses401(),
        ApiModels.methodResponses403(),
        ApiModels.methodResponses504(),
      ],
    });
  }

  private responseModel() {
    return new Model(this.scope, `${this.baseId}-resp-model`, {
      restApi: this.router.api,
      modelName: 'ListCheckpointsResponse',
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
              page: {
                type: JsonSchemaType.INTEGER,
              },
              per_page: {
                type: JsonSchemaType.INTEGER,
              },
              pages: {
                type: JsonSchemaType.INTEGER,
              },
              total: {
                type: JsonSchemaType.INTEGER,
              },
              checkpoints: {
                type: JsonSchemaType.ARRAY,
                items: {
                  type: JsonSchemaType.OBJECT,
                  properties: {
                    id: {
                      type: JsonSchemaType.STRING,
                    },
                    s3Location: {
                      type: JsonSchemaType.STRING,
                    },
                    type: {
                      type: JsonSchemaType.STRING,
                    },
                    status: {
                      type: JsonSchemaType.STRING,
                    },
                    name: {
                      type: JsonSchemaType.ARRAY,
                      items: {
                        type: JsonSchemaType.STRING,
                      },
                    },
                    created: {
                      type: JsonSchemaType.STRING,
                    },
                    params: {
                      type: [JsonSchemaType.OBJECT, JsonSchemaType.NULL],
                      properties: {
                        creator: {
                          type: JsonSchemaType.STRING,
                        },
                        multipart_upload: {
                          type: JsonSchemaType.OBJECT,
                          properties: {
                            '.*': {
                              type: JsonSchemaType.OBJECT,
                              properties: {
                                uploadId: {
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
                                'uploadId',
                              ],
                            },
                          },
                        },
                        message: {
                          type: JsonSchemaType.STRING,
                        },
                        created: {
                          type: JsonSchemaType.STRING,
                        },
                      },
                      required: [
                        'created',
                        'creator',
                        'message',
                        'multipart_upload',
                      ],
                    },
                    allowed_roles_or_users: {
                      type: JsonSchemaType.ARRAY,
                      items: {
                        type: JsonSchemaType.STRING,
                      },
                    },
                  },
                  required: [
                    'allowed_roles_or_users',
                    'created',
                    'id',
                    'name',
                    'params',
                    's3Location',
                    'status',
                    'type',
                  ],
                },
              },
            },
            required: [
              'checkpoints',
              'page',
              'pages',
              'per_page',
              'total',
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
      index: 'list_checkpoints.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.iamRole(),
      memorySize: 2048,
      tracing: aws_lambda.Tracing.ACTIVE,
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
      ],
      resources: [this.checkpointTable.tableArn, this.multiUserTable.tableArn],
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

}
