import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, aws_lambda, Duration } from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model, Resource } from 'aws-cdk-lib/aws-apigateway';
import { Table } from 'aws-cdk-lib/aws-dynamodb';
import { Effect, PolicyStatement, Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';
import { Architecture, LayerVersion, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Bucket } from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import { SCHEMA_DEBUG, SCHEMA_LAST_KEY, SCHEMA_MESSAGE } from '../../shared/schema';

export interface GetTrainingJobApiProps {
  router: Resource;
  httpMethod: string;
  trainingTable: Table;
  multiUserTable: Table;
  commonLayer: LayerVersion;
  s3Bucket: Bucket;
}

export class GetTrainingJobApi {
  private readonly router: Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly trainingTable: Table;
  private readonly multiUserTable: Table;
  private readonly layer: LayerVersion;
  private readonly baseId: string;
  private readonly s3Bucket: Bucket;

  constructor(scope: Construct, id: string, props: GetTrainingJobApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.trainingTable = props.trainingTable;
    this.multiUserTable = props.multiUserTable;
    this.layer = props.commonLayer;
    this.s3Bucket = props.s3Bucket;

    const lambdaFunction = this.apiLambda();

    const lambdaIntegration = new LambdaIntegration(
      lambdaFunction,
      { proxy: true },
    );

    this.router.addResource('{id}')
      .addMethod(this.httpMethod, lambdaIntegration, {
        apiKeyRequired: true,
        operationName: 'GetTraining',
        methodResponses: [
          ApiModels.methodResponse(this.responseModel()),
          ApiModels.methodResponses401(),
          ApiModels.methodResponses403(),
          ApiModels.methodResponses404(),
        ],
      },
      );
  }


  private responseModel() {
    return new Model(this.scope, `${this.baseId}-resp-model`, {
      restApi: this.router.api,
      modelName: 'GetTrainResponse',
      description: 'GetTrain Response Model',
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
                },
              },
              last_evaluated_key: SCHEMA_LAST_KEY,
            },
            required: [
              'trainings',
              'last_evaluated_key',
            ],
          },
        },
        required: [
          'statusCode',
          'debug',
          'data',
          'message',
        ],
      },
      contentType: 'application/json',
    });
  }


  private apiLambda() {
    return new PythonFunction(
      this.scope,
      `${this.baseId}-lambda`,
      {
        entry: '../middleware_api/trainings',
        architecture: Architecture.X86_64,
        runtime: Runtime.PYTHON_3_10,
        index: 'get_training_job.py',
        handler: 'handler',
        timeout: Duration.seconds(900),
        role: this.iamRole(),
        memorySize: 2048,
        tracing: aws_lambda.Tracing.ACTIVE,
        environment: {
          TRAINING_JOB_TABLE: this.trainingTable.tableName,
        },
        layers: [this.layer],
      });
  }


  private iamRole(): Role {

    const newRole = new Role(
      this.scope,
      `${this.baseId}-role`,
      {
        assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
      },
    );

    newRole.addToPolicy(new PolicyStatement({
      actions: [
        // get a training job
        'dynamodb:GetItem',
        'dynamodb:BatchGetItem',
        'dynamodb:Scan',
        'dynamodb:Query',
      ],
      resources: [
        this.trainingTable.tableArn,
        this.multiUserTable.tableArn,
      ],
    }));

    newRole.addToPolicy(new PolicyStatement({
      actions: [
        // get an object for training
        's3:GetObject',
      ],
      resources: [
        `${this.s3Bucket.bucketArn}`,
        `${this.s3Bucket.bucketArn}/*`,
      ],
    }));

    newRole.addToPolicy(new PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'logs:CreateLogGroup',
        'logs:CreateLogStream',
        'logs:PutLogEvents',
      ],
      resources: [`arn:${Aws.PARTITION}:logs:${Aws.REGION}:${Aws.ACCOUNT_ID}:log-group:*:*`],
    }));

    return newRole;
  }
}
