import { PythonFunction, PythonFunctionProps } from '@aws-cdk/aws-lambda-python-alpha';
import {
  aws_apigateway,
  aws_apigateway as apigw,
  aws_dynamodb,
  aws_iam,
  aws_lambda, aws_s3,
  Duration,
} from 'aws-cdk-lib';
import { MethodOptions } from 'aws-cdk-lib/aws-apigateway/lib/method';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';


export interface CreateDatasetApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  datasetItemTable: aws_dynamodb.Table;
  datasetInfoTable: aws_dynamodb.Table;
  srcRoot: string;
  commonLayer: aws_lambda.LayerVersion;
  s3Bucket: aws_s3.Bucket;
}

export class CreateDatasetApi {
  private readonly src;
  private readonly router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly datasetItemTable: aws_dynamodb.Table;
  private readonly datasetInfoTable: aws_dynamodb.Table;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly s3Bucket: aws_s3.Bucket;

  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: CreateDatasetApiProps) {
    this.scope = scope;
    this.httpMethod = props.httpMethod;
    this.datasetItemTable = props.datasetItemTable;
    this.datasetInfoTable = props.datasetInfoTable;
    this.baseId = id;
    this.router = props.router;
    this.src = props.srcRoot;
    this.layer = props.commonLayer;
    this.s3Bucket = props.s3Bucket;

    this.createDatasetApi();
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
        'dynamodb:BatchWriteItem',
        'dynamodb:PutItem',
        'dynamodb:UpdateItem',
        'dynamodb:DeleteItem',
      ],
      resources: [
        this.datasetItemTable.tableArn,
        this.datasetInfoTable.tableArn,
      ],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        's3:GetObject',
        's3:PutObject',
        's3:ListBucket',
        's3:DeleteObject',
        's3:AbortMultipartUpload',
        's3:ListMultipartUploadParts',
        's3:ListBucketMultipartUploads',
      ],
      resources: [
        `${this.s3Bucket.bucketArn}/*`,
        'arn:aws:s3:::*SageMaker*',
        'arn:aws:s3:::*Sagemaker*',
        'arn:aws:s3:::*sagemaker*',
      ],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'logs:CreateLogGroup',
        'logs:CreateLogStream',
        'logs:PutLogEvents',
      ],
      resources: ['*'],
    }));
    return newRole;
  }

  private createDatasetApi() {
    const lambdaFunction = new PythonFunction(this.scope, `${this.baseId}-create`, <PythonFunctionProps>{
      functionName: `${this.baseId}-create`,
      entry: `${this.src}/dataset_service`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_9,
      index: 'dataset_api.py',
      handler: 'create_dataset_api',
      timeout: Duration.seconds(900),
      role: this.iamRole(),
      memorySize: 1024,
      environment: {
        DATASET_ITEM_TABLE: this.datasetItemTable.tableName,
        DATASET_INFO_TABLE: this.datasetInfoTable.tableName,
        S3_BUCKET: this.s3Bucket.bucketName,
      },
      layers: [this.layer],
    });
    const createDatasetIntegration = new apigw.LambdaIntegration(
      lambdaFunction,
      {
        proxy: false,
        integrationResponses: [{ statusCode: '200' }],
      },
    );
    this.router.addMethod(this.httpMethod, createDatasetIntegration, <MethodOptions>{
      apiKeyRequired: true,
      methodResponses: [{
        statusCode: '200',
      }],
    });
  }
}

