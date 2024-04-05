import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, aws_lambda, Duration } from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model, Resource } from 'aws-cdk-lib/aws-apigateway';
import { Table } from 'aws-cdk-lib/aws-dynamodb';
import { Effect, PolicyStatement, Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';
import { Architecture, LayerVersion, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Bucket } from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import {
  SCHEMA_DEBUG,
  SCHEMA_MESSAGE,
  SCHEMA_TRAIN_CREATED,
  SCHEMA_TRAIN_ID,
  SCHEMA_TRAIN_MODEL_NAME,
  SCHEMA_TRAIN_PARAMS,
  SCHEMA_TRAIN_SAGEMAKER_NAME,
  SCHEMA_TRAIN_STATUS,
  SCHEMA_TRAIN_TYPE,
} from '../../shared/schema';

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
      description: 'Response Model GetTrainResponse',
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
            additionalProperties: true,
            properties: {
              id: SCHEMA_TRAIN_ID,
              modelName: SCHEMA_TRAIN_MODEL_NAME,
              status: SCHEMA_TRAIN_STATUS,
              trainType: SCHEMA_TRAIN_TYPE,
              created: SCHEMA_TRAIN_CREATED,
              sagemakerTrainName: SCHEMA_TRAIN_SAGEMAKER_NAME,
              params: SCHEMA_TRAIN_PARAMS,
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
