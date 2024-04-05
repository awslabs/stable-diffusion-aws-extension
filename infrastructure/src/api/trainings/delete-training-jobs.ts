import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, aws_lambda, Duration } from 'aws-cdk-lib';
import {
  JsonSchemaType,
  JsonSchemaVersion,
  LambdaIntegration,
  Model,
  RequestValidator,
  Resource,
} from 'aws-cdk-lib/aws-apigateway';
import { Table } from 'aws-cdk-lib/aws-dynamodb';
import { Effect, PolicyStatement, Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';
import { Architecture, LayerVersion, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Bucket } from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import { SCHEMA_TRAIN_ID } from '../../shared/schema';

export interface DeleteTrainingJobsApiProps {
  router: Resource;
  httpMethod: string;
  trainingTable: Table;
  multiUserTable: Table;
  commonLayer: LayerVersion;
  s3Bucket: Bucket;
}

export class DeleteTrainingJobsApi {
  private readonly router: Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly trainingTable: Table;
  private readonly multiUserTable: Table;
  private readonly layer: LayerVersion;
  private readonly baseId: string;
  private readonly s3Bucket: Bucket;

  constructor(scope: Construct, id: string, props: DeleteTrainingJobsApiProps) {
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

    this.router.addMethod(
      this.httpMethod,
      lambdaIntegration,
      {
        apiKeyRequired: true,
        requestValidator: this.createRequestValidator(),
        requestModels: {
          'application/json': this.createRequestBodyModel(),
        },
        operationName: 'DeleteTrainings',
        methodResponses: [
          ApiModels.methodResponses400(),
          ApiModels.methodResponses401(),
          ApiModels.methodResponses403(),
          ApiModels.methodResponses404(),
        ],
      });
  }

  private createRequestBodyModel(): Model {
    return new Model(
      this.scope,
      `${this.baseId}-model`,
      {
        restApi: this.router.api,
        modelName: this.baseId,
        description: `Request Model ${this.baseId}`,
        schema: {
          schema: JsonSchemaVersion.DRAFT7,
          title: this.baseId,
          type: JsonSchemaType.OBJECT,
          properties: {
            training_id_list: {
              type: JsonSchemaType.ARRAY,
              items: SCHEMA_TRAIN_ID,
              minItems: 1,
              maxItems: 100,
            },
          },
          required: [
            'training_id_list',
          ],
        },
        contentType: 'application/json',
      });
  }

  private createRequestValidator(): RequestValidator {
    return new RequestValidator(
      this.scope,
      `${this.baseId}-del-train-validator`,
      {
        restApi: this.router.api,
        validateRequestBody: true,
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
        index: 'delete_training_jobs.py',
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
        // delete a training job
        'dynamodb:DeleteItem',
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
        // list training objects by prefix
        's3:ListBucket',
        // delete training file
        's3:DeleteObject',
      ],
      resources: [
        `${this.s3Bucket.bucketArn}`,
        `${this.s3Bucket.bucketArn}/*`,
      ],
    }));

    newRole.addToPolicy(new PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'sagemaker:StopTrainingJob',
      ],
      resources: [
        `arn:${Aws.PARTITION}:sagemaker:${Aws.REGION}:${Aws.ACCOUNT_ID}:training-job/*`,
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
