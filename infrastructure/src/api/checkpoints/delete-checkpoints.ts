import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, aws_lambda, Duration } from 'aws-cdk-lib';
import {
  JsonSchemaType,
  JsonSchemaVersion,
  LambdaIntegration,
  Model,
  Resource,
} from 'aws-cdk-lib/aws-apigateway';
import { Table } from 'aws-cdk-lib/aws-dynamodb';
import { Effect, PolicyStatement, Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';
import { Architecture, LayerVersion, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Bucket } from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import { SCHEMA_CHECKPOINT_ID } from '../../shared/schema';
import { ApiValidators } from '../../shared/validator';

export interface DeleteCheckpointsApiProps {
  router: Resource;
  httpMethod: string;
  checkPointsTable: Table;
  userTable: Table;
  commonLayer: LayerVersion;
  s3Bucket: Bucket;
}

export class DeleteCheckpointsApi {
  public router: Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly checkPointsTable: Table;
  private readonly userTable: Table;
  private readonly layer: LayerVersion;
  private readonly baseId: string;
  private readonly s3Bucket: Bucket;

  constructor(scope: Construct, id: string, props: DeleteCheckpointsApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.checkPointsTable = props.checkPointsTable;
    this.userTable = props.userTable;
    this.layer = props.commonLayer;
    this.s3Bucket = props.s3Bucket;

    const lambdaFunction = this.apiLambda();

    const lambdaIntegration = new LambdaIntegration(lambdaFunction, { proxy: true });

    this.router.addMethod(
      this.httpMethod,
      lambdaIntegration,
      {
        apiKeyRequired: true,
        requestValidator: ApiValidators.validator,
        requestModels: {
          'application/json': this.createRequestBodyModel(),
        },
        operationName: 'DeleteCheckpoints',
        methodResponses: [
          ApiModels.methodResponses204(),
          ApiModels.methodResponses400(),
          ApiModels.methodResponses401(),
          ApiModels.methodResponses403(),
          ApiModels.methodResponses504(),
        ],
      });
  }

  private createRequestBodyModel() {
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
            checkpoint_id_list: {
              type: JsonSchemaType.ARRAY,
              items: SCHEMA_CHECKPOINT_ID,
              minItems: 1,
              maxItems: 100,
            },
          },
          required: [
            'checkpoint_id_list',
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
        entry: '../middleware_api/checkpoints',
        architecture: Architecture.X86_64,
        runtime: Runtime.PYTHON_3_10,
        index: 'delete_checkpoints.py',
        handler: 'handler',
        timeout: Duration.seconds(900),
        role: this.iamRole(),
        memorySize: 2048,
        tracing: aws_lambda.Tracing.ACTIVE,
        environment: {
          CHECKPOINTS_TABLE: this.checkPointsTable.tableName,
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
        // get checkpoint
        'dynamodb:GetItem',
        // delete checkpoint
        'dynamodb:DeleteItem',
        // query users
        'dynamodb:Query',
        'dynamodb:Scan',
      ],
      resources: [
        this.checkPointsTable.tableArn,
        this.userTable.tableArn,
      ],
    }));

    newRole.addToPolicy(new PolicyStatement({
      actions: [
        // list checkpoint objects by prefix
        's3:ListBucket',
        // delete checkpoint file
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
        'logs:CreateLogGroup',
        'logs:CreateLogStream',
        'logs:PutLogEvents',
      ],
      resources: [`arn:${Aws.PARTITION}:logs:${Aws.REGION}:${Aws.ACCOUNT_ID}:log-group:*:*`],
    }));

    return newRole;
  }
}
