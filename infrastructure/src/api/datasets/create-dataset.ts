import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, aws_apigateway, aws_dynamodb, aws_iam, aws_lambda, aws_s3, Duration } from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model } from 'aws-cdk-lib/aws-apigateway';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import { SCHEMA_DATASET_NAME, SCHEMA_DEBUG, SCHEMA_MESSAGE } from '../../shared/schema';
import { ApiValidators } from '../../shared/validator';


export interface CreateDatasetApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  datasetItemTable: aws_dynamodb.Table;
  datasetInfoTable: aws_dynamodb.Table;
  multiUserTable: aws_dynamodb.Table;
  commonLayer: aws_lambda.LayerVersion;
  s3Bucket: aws_s3.Bucket;
}

export class CreateDatasetApi {
  private readonly router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly datasetItemTable: aws_dynamodb.Table;
  private readonly multiUserTable: aws_dynamodb.Table;
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
    this.layer = props.commonLayer;
    this.s3Bucket = props.s3Bucket;
    this.multiUserTable = props.multiUserTable;

    const lambdaFunction = this.apiLambda();

    const lambdaIntegration = new LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.addMethod(this.httpMethod, lambdaIntegration, {
      apiKeyRequired: true,
      requestValidator: ApiValidators.bodyValidator,
      requestModels: {
        'application/json': this.createRequestBodyModel(),
      },
      operationName: 'CreateDataset',
      methodResponses: [
        ApiModels.methodResponse(this.responseModel(), '201'),
        ApiModels.methodResponses400(),
        ApiModels.methodResponses401(),
        ApiModels.methodResponses403(),
        ApiModels.methodResponses504(),
      ],
    });
  }

  private responseModel() {
    return new Model(this.scope, `${this.baseId}-resp-model`, {
      restApi: this.router.api,
      modelName: 'CreateDatasetResponse',
      description: `Response Model ${this.baseId}`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        type: JsonSchemaType.OBJECT,
        title: 'CreateDatasetResponse',
        properties: {
          statusCode: {
            type: JsonSchemaType.INTEGER,
            enum: [201],
          },
          debug: SCHEMA_DEBUG,
          message: SCHEMA_MESSAGE,
          data: {
            type: JsonSchemaType.OBJECT,
            properties: {
              datasetName: SCHEMA_DATASET_NAME,
              s3PresignUrl: {
                type: JsonSchemaType.OBJECT,
                patternProperties: {
                  '.*': {
                    type: JsonSchemaType.STRING,
                    format: 'uri',
                    description: 'S3 Presign URL',
                  },
                },
              },
            },
            required: [
              'datasetName',
              's3PresignUrl',
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
        'dynamodb:BatchWriteItem',
        'dynamodb:PutItem',
        'dynamodb:UpdateItem',
        'dynamodb:DeleteItem',
      ],
      resources: [
        this.datasetItemTable.tableArn,
        this.datasetInfoTable.tableArn,
        this.multiUserTable.tableArn,
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
        `arn:${Aws.PARTITION}:s3:::*SageMaker*`,
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
          dataset_name: {
            type: JsonSchemaType.STRING,
            minLength: 1,
            maxLength: 20,
            pattern: '^[A-Za-z][A-Za-z0-9_-]*$',
          },
          content: {
            type: JsonSchemaType.ARRAY,
            items: {
              type: JsonSchemaType.OBJECT,
              properties: {
                filename: {
                  type: JsonSchemaType.STRING,
                  minLength: 1,
                },
                name: {
                  type: JsonSchemaType.STRING,
                  minLength: 1,
                },
                type: {
                  type: JsonSchemaType.STRING,
                  minLength: 1,
                },
                params: {
                  type: JsonSchemaType.OBJECT,
                },
              },
            },
            minItems: 1,
            maxItems: 500,
          },
          creator: {
            type: JsonSchemaType.STRING,
            minLength: 1,
          },
          prefix: {
            type: JsonSchemaType.STRING,
            minLength: 0,
          },
          params: {
            type: JsonSchemaType.OBJECT,
            properties: {
              description: {
                type: JsonSchemaType.STRING,
              },
            },
          },
        },
        required: [
          'dataset_name',
          'content',
          'creator',
          'prefix',
        ],
      },
      contentType: 'application/json',
    });
  }

  private apiLambda() {
    return new PythonFunction(this.scope, `${this.baseId}-lambda`, {
      entry: '../middleware_api/datasets',
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'create_dataset.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.iamRole(),
      memorySize: 2048,
      tracing: aws_lambda.Tracing.ACTIVE,
      environment: {
        DATASET_ITEM_TABLE: this.datasetItemTable.tableName,
        DATASET_INFO_TABLE: this.datasetInfoTable.tableName,
      },
      layers: [this.layer],
    });
  }


}

