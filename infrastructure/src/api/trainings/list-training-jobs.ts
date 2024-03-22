import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import {
  aws_apigateway,
  aws_dynamodb,
  aws_iam,
  aws_lambda,
  aws_s3,
  CfnParameter,
  Duration,
} from 'aws-cdk-lib';
import { MethodOptions } from 'aws-cdk-lib/aws-apigateway/lib/method';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';


export interface ListTrainingJobsApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  trainTable: aws_dynamodb.Table;
  multiUserTable: aws_dynamodb.Table;
  srcRoot: string;
  commonLayer: aws_lambda.LayerVersion;
  s3Bucket: aws_s3.Bucket;
  logLevel: CfnParameter;
}

export class ListTrainingJobsApi {
  private readonly src;
  private readonly router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly trainTable: aws_dynamodb.Table;
  private readonly multiUserTable: aws_dynamodb.Table;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly s3Bucket: aws_s3.Bucket;
  private readonly logLevel: CfnParameter;
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
    this.s3Bucket = props.s3Bucket;
    this.logLevel = props.logLevel;

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
      environment: {
        TRAIN_TABLE: this.trainTable.tableName,
        S3_BUCKET: this.s3Bucket.bucketName,
        MULTI_USER_TABLE: this.multiUserTable.tableName,
        LOG_LEVEL: this.logLevel.valueAsString,
      },
      layers: [this.layer],
    });

    const listTrainJobsIntegration = new aws_apigateway.LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );
    this.router.addMethod(this.httpMethod, listTrainJobsIntegration, <MethodOptions>{
      apiKeyRequired: true,
    });
  }
}

