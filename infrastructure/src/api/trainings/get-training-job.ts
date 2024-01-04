import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import {Aws, CfnParameter, Duration} from 'aws-cdk-lib';
import { LambdaIntegration, Resource } from 'aws-cdk-lib/aws-apigateway';
import { Table } from 'aws-cdk-lib/aws-dynamodb';
import { Effect, PolicyStatement, Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';
import { Architecture, LayerVersion, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Bucket } from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';

export interface GetTrainingJobApiProps {
  router: Resource;
  httpMethod: string;
  trainingTable: Table;
  srcRoot: string;
  commonLayer: LayerVersion;
  s3Bucket: Bucket;
  logLevel: CfnParameter;
}

export class GetTrainingJobApi {
  private readonly src: string;
  private readonly router: Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly trainingTable: Table;
  private readonly layer: LayerVersion;
  private readonly baseId: string;
  private readonly s3Bucket: Bucket;
  private readonly logLevel: CfnParameter;

  constructor(scope: Construct, id: string, props: GetTrainingJobApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.trainingTable = props.trainingTable;
    this.src = props.srcRoot;
    this.layer = props.commonLayer;
    this.s3Bucket = props.s3Bucket;
    this.logLevel = props.logLevel;

    this.getTrainingJobApi();
  }

  private getTrainingJobApi() {

    const lambdaFunction = new PythonFunction(
      this.scope,
      `${this.baseId}-lambda`,
      {
        entry: `${this.src}/trainings`,
        architecture: Architecture.X86_64,
        runtime: Runtime.PYTHON_3_9,
        index: 'get_training_job.py',
        handler: 'handler',
        timeout: Duration.seconds(900),
        role: this.iamRole(),
        memorySize: 1024,
        environment: {
          TRAINING_JOB_TABLE: this.trainingTable.tableName,
          S3_BUCKET_NAME: this.s3Bucket.bucketName,
          LOG_LEVEL: this.logLevel.valueAsString,
        },
        layers: [this.layer],
      });

    const lambdaIntegration = new LambdaIntegration(
      lambdaFunction,
      { proxy: true },
    );

    this.router.addMethod(this.httpMethod, lambdaIntegration, { apiKeyRequired: true });

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
      ],
      resources: [
        this.trainingTable.tableArn,
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
