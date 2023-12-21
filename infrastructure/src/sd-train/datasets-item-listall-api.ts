import { PythonFunction, PythonFunctionProps } from '@aws-cdk/aws-lambda-python-alpha';
import {
  Aws,
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


export interface ListAllDatasetItemsApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  datasetInfoTable: aws_dynamodb.Table;
  datasetItemsTable: aws_dynamodb.Table;
  multiUserTable: aws_dynamodb.Table;
  srcRoot: string;
  commonLayer: aws_lambda.LayerVersion;
  s3Bucket: aws_s3.Bucket;
  authorizer: aws_apigateway.IAuthorizer;
}

export class ListAllDatasetItemsApi {
  private readonly src;
  private readonly router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly datasetInfoTable: aws_dynamodb.Table;
  private readonly datasetItemsTable: aws_dynamodb.Table;
  private readonly multiUserTable: aws_dynamodb.Table;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly s3Bucket: aws_s3.Bucket;
  private readonly authorizer: aws_apigateway.IAuthorizer;

  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: ListAllDatasetItemsApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.datasetInfoTable = props.datasetInfoTable;
    this.datasetItemsTable = props.datasetItemsTable;
    this.multiUserTable = props.multiUserTable;
    this.src = props.srcRoot;
    this.layer = props.commonLayer;
    this.s3Bucket = props.s3Bucket;
    this.authorizer = props.authorizer;

    this.listAllDatasetApi();
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
        this.datasetInfoTable.tableArn,
        this.datasetItemsTable.tableArn,
        this.multiUserTable.tableArn,
      ],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        's3:GetObject',
        's3:ListBucket',
      ],
      resources: [`${this.s3Bucket.bucketArn}/*`,
        `arn:${Aws.PARTITION}:s3:::*SageMaker*`,
        `arn:${Aws.PARTITION}:s3:::*Sagemaker*`,
        `arn:${Aws.PARTITION}:s3:::*sagemaker*`],
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

  private listAllDatasetApi() {
    const lambdaFunction = new PythonFunction(this.scope, `${this.baseId}-lambda`, <PythonFunctionProps>{
      entry: `${this.src}/dataset_service`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_9,
      index: 'dataset_api.py',
      handler: 'list_data_by_dataset',
      timeout: Duration.seconds(900),
      role: this.iamRole(),
      memorySize: 1024,
      environment: {
        DATASET_ITEM_TABLE: this.datasetItemsTable.tableName,
        DATASET_INFO_TABLE: this.datasetInfoTable.tableName,
        MULTI_USER_TABLE: this.multiUserTable.tableName,
        S3_BUCKET: this.s3Bucket.bucketName,
      },
      layers: [this.layer],
    });

    const listDatasetItemsIntegration = new apigw.LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.getResource('{id}')
        ?.addMethod(this.httpMethod, listDatasetItemsIntegration, <MethodOptions>{
          apiKeyRequired: true,
          authorizer: this.authorizer,
        });
  }
}

