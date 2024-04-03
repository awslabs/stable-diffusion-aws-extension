import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { aws_apigateway, aws_dynamodb, aws_iam, aws_lambda, Duration } from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, Model } from 'aws-cdk-lib/aws-apigateway';
import { MethodOptions } from 'aws-cdk-lib/aws-apigateway/lib/method';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import { SCHEMA_DEBUG } from '../../shared/schema';


export interface ListTrainingJobsApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  trainTable: aws_dynamodb.Table;
  multiUserTable: aws_dynamodb.Table;
  srcRoot: string;
  commonLayer: aws_lambda.LayerVersion;
}

export class ListTrainingJobsApi {
  private readonly src;
  private readonly router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly trainTable: aws_dynamodb.Table;
  private readonly multiUserTable: aws_dynamodb.Table;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: ListTrainingJobsApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.trainTable = props.trainTable;
    this.multiUserTable = props.multiUserTable;
    this.src = props.srcRoot;
    this.layer = props.commonLayer;

    this.listAllTrainJobsApi();
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
        this.trainTable.tableArn,
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

  private listAllTrainJobsApi() {
    const lambdaFunction = new PythonFunction(this.scope, `${this.baseId}-lambda`, {
      entry: `${this.src}/trainings`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'list_training_jobs.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.iamRole(),
      memorySize: 2048,
      tracing: aws_lambda.Tracing.ACTIVE,
      environment: {
        TRAIN_TABLE: this.trainTable.tableName,
      },
      layers: [this.layer],
    });

    const lambdaIntegration = new aws_apigateway.LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.addMethod(this.httpMethod, lambdaIntegration, <MethodOptions>{
      apiKeyRequired: true,
      operationName: 'ListTrainings',
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
      modelName: 'ListTrainingsResponse',
      description: 'ListTrainings Response Model',
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
          data: {
            type: JsonSchemaType.OBJECT,
            properties: {
              trainings: {
                type: JsonSchemaType.ARRAY,
                items: {
                  type: JsonSchemaType.OBJECT,
                  properties: {
                    id: {
                      type: JsonSchemaType.STRING,
                      pattern: '^[a-f0-9\\-]{36}$',
                    },
                    modelName: {
                      type: JsonSchemaType.STRING,
                    },
                    status: {
                      type: JsonSchemaType.STRING,
                    },
                    trainType: {
                      type: JsonSchemaType.STRING,
                    },
                    created: {
                      type: JsonSchemaType.STRING,
                      pattern: '^\\d{10}(\\.\\d+)?$',
                    },
                    sagemakerTrainName: {
                      type: JsonSchemaType.STRING,
                    },
                    params: {
                      type: JsonSchemaType.OBJECT,
                      properties: {
                        training_params: {
                          type: JsonSchemaType.OBJECT,
                        },
                        training_type: {
                          type: JsonSchemaType.STRING,
                        },
                        config_params: {
                          type: JsonSchemaType.OBJECT,
                          properties: {
                            saving_arguments: {
                              type: JsonSchemaType.OBJECT,
                            },
                            training_arguments: {
                              type: JsonSchemaType.OBJECT,
                            },
                          },
                          required: [
                            'saving_arguments',
                            'training_arguments',
                          ],
                        },
                      },
                      required: [
                        'training_params',
                        'training_type',
                        'config_params',
                      ],
                    },
                  },
                  required: [
                    'id',
                    'modelName',
                    'status',
                    'trainType',
                    'created',
                    'sagemakerTrainName',
                    'params',
                  ],
                  additionalProperties: false,
                },
              },
              last_evaluated_key: {
                type: [
                  JsonSchemaType.STRING,
                  JsonSchemaType.NULL,
                ],
              },
            },
            required: [
              'trainings',
              'last_evaluated_key',
            ],
            additionalProperties: false,
          },
          message: {
            type: JsonSchemaType.STRING,
            enum: ['OK'],
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
}

