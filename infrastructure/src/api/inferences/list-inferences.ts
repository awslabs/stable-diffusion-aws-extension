import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { aws_apigateway, aws_dynamodb, aws_iam, aws_lambda, Duration } from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model } from 'aws-cdk-lib/aws-apigateway';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import { SCHEMA_DEBUG, SCHEMA_LAST_KEY, SCHEMA_MESSAGE } from '../../shared/schema';


export interface ListInferencesApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  endpointDeploymentTable: aws_dynamodb.Table;
  multiUserTable: aws_dynamodb.Table;
  inferenceJobTable: aws_dynamodb.Table;
  commonLayer: aws_lambda.LayerVersion;
}

export class ListInferencesApi {
  private readonly router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly endpointDeploymentTable: aws_dynamodb.Table;
  private readonly multiUserTable: aws_dynamodb.Table;
  private readonly inferenceJobTable: aws_dynamodb.Table;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly baseId: string;


  constructor(scope: Construct, id: string, props: ListInferencesApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.multiUserTable = props.multiUserTable;
    this.inferenceJobTable = props.inferenceJobTable;
    this.endpointDeploymentTable = props.endpointDeploymentTable;
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
      operationName: 'ListInferences',
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
      modelName: 'ListInferencesResponse',
      description: 'ListInferences Response Model',
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        title: this.baseId,
        type: JsonSchemaType.OBJECT,
        properties: {
          statusCode: {
            type: JsonSchemaType.INTEGER,
            enum: [200],
          },
          debug: SCHEMA_DEBUG,
          message: SCHEMA_MESSAGE,
          data: {
            type: JsonSchemaType.OBJECT,
            properties: {
              inferences: {
                type: JsonSchemaType.ARRAY,
                items: {
                  type: JsonSchemaType.OBJECT,
                  properties: {
                    InferenceJobId: {
                      type: JsonSchemaType.STRING,
                      pattern: '^[a-f0-9\\-]{36}$',
                    },
                    status: {
                      type: JsonSchemaType.STRING,
                    },
                    taskType: {
                      type: JsonSchemaType.STRING,
                    },
                    owner_group_or_role: {
                      type: JsonSchemaType.ARRAY,
                      items: {
                        type: JsonSchemaType.STRING,
                      },
                    },
                    inference_info_name: {
                      type: JsonSchemaType.STRING,
                    },
                    startTime: {
                      type: JsonSchemaType.STRING,
                      format: 'date-time',
                    },
                    createTime: {
                      type: JsonSchemaType.STRING,
                      format: 'date-time',
                    },
                    image_names: {
                      type: JsonSchemaType.ARRAY,
                      items: {
                        type: JsonSchemaType.STRING,
                      },
                    },
                    sagemakerRaw: {
                      type: JsonSchemaType.OBJECT,
                    },
                    completeTime: {
                      type: JsonSchemaType.STRING,
                      format: 'date-time',
                    },
                    params: {
                      type: JsonSchemaType.OBJECT,
                      properties: {
                        input_body_s3: {
                          type: JsonSchemaType.STRING,
                          format: 'uri',
                        },
                        sagemaker_inference_endpoint_id: {
                          type: JsonSchemaType.STRING,
                          pattern: '^[a-f0-9\\-]{36}$',
                        },
                        input_body_presign_url: {
                          type: JsonSchemaType.STRING,
                          format: 'uri',
                        },
                        used_models: {
                          type: JsonSchemaType.OBJECT,
                          additionalProperties: {
                            type: JsonSchemaType.ARRAY,
                            items: {
                              type: JsonSchemaType.OBJECT,
                              properties: {
                                s3: {
                                  type: JsonSchemaType.STRING,
                                  format: 'uri',
                                },
                                id: {
                                  type: JsonSchemaType.STRING,
                                  pattern: '^[a-f0-9\\-]{36}$',
                                },
                                model_name: {
                                  type: JsonSchemaType.STRING,
                                },
                                type: {
                                  type: JsonSchemaType.STRING,
                                },
                              },
                              required: [
                                's3',
                                'id',
                                'model_name',
                                'type',
                              ],
                              additionalProperties: false,
                            },
                          },
                        },
                        output_path: {
                          type: JsonSchemaType.STRING,
                          format: 'uri',
                        },
                        sagemaker_inference_instance_type: {
                          type: JsonSchemaType.STRING,
                        },
                        sagemaker_inference_endpoint_name: {
                          type: JsonSchemaType.STRING,
                        },
                      },
                      required: [
                        'input_body_s3',
                        'sagemaker_inference_endpoint_id',
                        'used_models',
                        'sagemaker_inference_instance_type',
                        'sagemaker_inference_endpoint_name',
                      ],
                      additionalProperties: false,
                    },
                    inference_type: {
                      type: JsonSchemaType.STRING,
                    },
                    payload_string: {
                      type: JsonSchemaType.STRING,
                    },
                  },
                  required: [
                    'InferenceJobId',
                    'status',
                    'taskType',
                    'owner_group_or_role',
                    'inference_info_name',
                    'startTime',
                    'createTime',
                    'image_names',
                    'completeTime',
                    'params',
                    'inference_type',
                  ],
                  additionalProperties: false,
                },
              },
              last_evaluated_key: SCHEMA_LAST_KEY,
            },
            required: [
              'inferences',
              'last_evaluated_key',
            ],
            additionalProperties: false,
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
      resources: [
        this.endpointDeploymentTable.tableArn,
        this.inferenceJobTable.tableArn,
        `${this.inferenceJobTable.tableArn}/*`,
        this.multiUserTable.tableArn,
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
    return newRole;
  }

  private apiLambda() {
    return new PythonFunction(this.scope, `${this.baseId}-lambda`, {
      entry: '../middleware_api/inferences',
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'list_inferences.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.iamRole(),
      memorySize: 2048,
      tracing: aws_lambda.Tracing.ACTIVE,
      environment: {
        INFERENCE_JOB_TABLE: this.inferenceJobTable.tableName,
      },
      layers: [this.layer],
    });
  }

}

