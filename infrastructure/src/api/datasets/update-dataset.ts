import { PythonFunction, PythonFunctionProps } from '@aws-cdk/aws-lambda-python-alpha';
import {
  Aws,
  aws_apigateway,
  aws_apigateway as apigw,
  aws_dynamodb,
  aws_iam,
  aws_lambda,
  aws_s3,
  CfnParameter,
  Duration,
} from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, Model, RequestValidator } from 'aws-cdk-lib/aws-apigateway';
import { MethodOptions } from 'aws-cdk-lib/aws-apigateway/lib/method';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';


export interface UpdateDatasetApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  datasetInfoTable: aws_dynamodb.Table;
  datasetItemTable: aws_dynamodb.Table;
  srcRoot: string;
  commonLayer: aws_lambda.LayerVersion;
  s3Bucket: aws_s3.Bucket;
  logLevel: CfnParameter;
}

export class UpdateDatasetApi {
  public readonly router: aws_apigateway.Resource;
  private readonly src;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly datasetInfoTable: aws_dynamodb.Table;
  private readonly datasetItemTable: aws_dynamodb.Table;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly s3Bucket: aws_s3.Bucket;
  private readonly logLevel: CfnParameter;
  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: UpdateDatasetApiProps) {
    this.scope = scope;
    this.src = props.srcRoot;
    this.layer = props.commonLayer;
    this.baseId = id;
    this.router = props.router;
    this.datasetInfoTable = props.datasetInfoTable;
    this.datasetItemTable = props.datasetItemTable;
    this.httpMethod = props.httpMethod;
    this.s3Bucket = props.s3Bucket;
    this.logLevel = props.logLevel;

    this.updateDatasetApi();
  }

  private iamRole(): aws_iam.Role {
    const newRole = new aws_iam.Role(this.scope, `${this.baseId}-update-role`, {
      assumedBy: new aws_iam.ServicePrincipal('lambda.amazonaws.com'),
    });
    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'dynamodb:BatchGetItem',
        'dynamodb:BatchWriteItem',
        'dynamodb:GetItem',
        'dynamodb:Scan',
        'dynamodb:Query',
        'dynamodb:UpdateItem',
      ],
      resources: [
        this.datasetItemTable.tableArn,
        this.datasetInfoTable.tableArn,
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

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        's3:GetObject',
        's3:PutObject',
        's3:DeleteObject',
        's3:ListBucket',
        's3:AbortMultipartUpload',
        's3:ListMultipartUploadParts',
        's3:ListBucketMultipartUploads',
      ],
      resources: [`${this.s3Bucket.bucketArn}/*`,
        `arn:${Aws.PARTITION}:s3:::*SageMaker*`,
        `arn:${Aws.PARTITION}:s3:::*Sagemaker*`,
        `arn:${Aws.PARTITION}:s3:::*sagemaker*`],
    }));
    return newRole;
  }

  private updateDatasetApi() {
    const lambdaFunction = new PythonFunction(this.scope, `${this.baseId}-lambda`, <PythonFunctionProps>{
      entry: `${this.src}/datasets`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_9,
      index: 'update_dataset.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.iamRole(),
      memorySize: 1024,
      environment: {
        DATASET_ITEM_TABLE: this.datasetItemTable.tableName,
        DATASET_INFO_TABLE: this.datasetInfoTable.tableName,
        S3_BUCKET: this.s3Bucket.bucketName,
        LOG_LEVEL: this.logLevel.valueAsString,
      },
      layers: [this.layer],
    });

    const requestModel = new Model(this.scope, `${this.baseId}-model`, {
      restApi: this.router.api,
      modelName: this.baseId,
      description: `${this.baseId} Request Model`,
      schema: {
        schema: JsonSchemaVersion.DRAFT4,
        title: this.baseId,
        type: JsonSchemaType.OBJECT,
        properties: {
          status: {
            type: JsonSchemaType.STRING,
            minLength: 1,
          },
        },
        required: [
          'status',
        ],
      },
      contentType: 'application/json',
    });

    const requestValidator = new RequestValidator(
      this.scope,
      `${this.baseId}-validator`,
      {
        restApi: this.router.api,
        requestValidatorName: this.baseId,
        validateRequestBody: true,
      });

    const createModelIntegration = new apigw.LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );
    this.router.addResource('{id}')
      .addMethod(this.httpMethod, createModelIntegration, <MethodOptions>{
        apiKeyRequired: true,
        requestValidator,
        requestModels: {
          'application/json': requestModel,
        },
      });
  }
}

