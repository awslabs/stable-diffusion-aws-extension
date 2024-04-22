import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, aws_apigateway, aws_dynamodb, aws_iam, aws_lambda, aws_s3, Duration } from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model } from 'aws-cdk-lib/aws-apigateway';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import { SCHEMA_DATASET_NAME, SCHEMA_DEBUG, SCHEMA_MESSAGE } from '../../shared/schema';
import { ApiValidators } from '../../shared/validator';


export interface CropDatasetApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  datasetInfoTable: aws_dynamodb.Table;
  datasetItemsTable: aws_dynamodb.Table;
  multiUserTable: aws_dynamodb.Table;
  commonLayer: aws_lambda.LayerVersion;
  s3Bucket: aws_s3.Bucket;
}

export class CropDatasetApi {
  private readonly router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly datasetInfoTable: aws_dynamodb.Table;
  private readonly datasetItemsTable: aws_dynamodb.Table;
  private readonly multiUserTable: aws_dynamodb.Table;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly s3Bucket: aws_s3.Bucket;
  private readonly baseId: string;
  private readonly role: aws_iam.Role;

  constructor(scope: Construct, id: string, props: CropDatasetApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.datasetInfoTable = props.datasetInfoTable;
    this.datasetItemsTable = props.datasetItemsTable;
    this.multiUserTable = props.multiUserTable;
    this.layer = props.commonLayer;
    this.s3Bucket = props.s3Bucket;

    this.role = this.iamRole();

    const lambda: PythonFunction = this.cropLambda();

    const lambdaFunction = this.apiLambda(lambda);

    const lambdaIntegration = new LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.getResource('{id}')
      ?.addResource('crop')
      ?.addMethod(this.httpMethod, lambdaIntegration, {
        apiKeyRequired: true,
        requestModels: {
          'application/json': this.createRequestBodyModel(),
        },
        requestValidator: ApiValidators.bodyValidator,
        operationName: 'CropDataset',
        methodResponses: [
          ApiModels.methodResponse(this.responseModel(), '201'),
          ApiModels.methodResponses401(),
          ApiModels.methodResponses403(),
          ApiModels.methodResponses404(),
        ],
      });
  }

  private createRequestBodyModel(): Model {
    return new Model(this.scope, `${this.baseId}-model`, {
      restApi: this.router.api,
      modelName: this.baseId,
      description: `Request Model ${this.baseId}`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        title: this.baseId,
        type: JsonSchemaType.OBJECT,
        properties: {
          max_resolution: {
            type: JsonSchemaType.STRING,
            description: 'Max resolution of the image, like: 512x512',
          },
        },
        required: [
          'max_resolution',
        ],
      },
      contentType: 'application/json',
    });
  }

  private responseModel() {
    return new Model(this.scope, `${this.baseId}-resp-model`, {
      restApi: this.router.api,
      modelName: 'CropDatasetResponse',
      description: `Response Model ${this.baseId}`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        type: JsonSchemaType.OBJECT,
        title: 'CropDatasetResponse',
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
              dataset_name: SCHEMA_DATASET_NAME,
            },
            required: [
              'dataset_name',
            ],
          },
        },
        required: [
          'statusCode',
          'debug',
          'data',
          'message',
        ],
      }
      ,
      contentType: 'application/json',
    });
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
        'lambda:invokeFunction',
      ],
      resources: [
        `arn:${Aws.PARTITION}:lambda:${Aws.REGION}:${Aws.ACCOUNT_ID}:function:*${this.baseId}*`,
      ],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        's3:GetObject',
        's3:ListBucket',
      ],
      resources: [`${this.s3Bucket.bucketArn}/*`,
        `arn:${Aws.PARTITION}:s3:::*SageMaker*`],
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

  private apiLambda(lambda: PythonFunction) {
    return new PythonFunction(this.scope, `${this.baseId}-lambda`, {
      entry: '../middleware_api/datasets',
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'crop_dataset.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.role,
      memorySize: 2048,
      tracing: aws_lambda.Tracing.ACTIVE,
      environment: {
        DATASET_ITEM_TABLE: this.datasetItemsTable.tableName,
        DATASET_INFO_TABLE: this.datasetInfoTable.tableName,
        CROP_LAMBDA_NAME: lambda.functionName,
      },
      layers: [this.layer],
    });
  }

  private cropLambda() {
    return new PythonFunction(this.scope, `${this.baseId}-crop-lambda`, {
      entry: '../middleware_api/datasets',
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'crop_dataset.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.role,
      memorySize: 2048,
      tracing: aws_lambda.Tracing.ACTIVE,
      environment: {
        DATASET_ITEM_TABLE: this.datasetItemsTable.tableName,
        DATASET_INFO_TABLE: this.datasetInfoTable.tableName,
      },
      layers: [this.layer],
    });
  }


}

