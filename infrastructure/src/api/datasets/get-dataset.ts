import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, aws_apigateway, aws_dynamodb, aws_iam, aws_lambda, aws_s3, Duration } from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, Model } from 'aws-cdk-lib/aws-apigateway';
import { MethodOptions } from 'aws-cdk-lib/aws-apigateway/lib/method';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import { SCHEMA_DEBUG } from '../../shared/schema';


export interface GetDatasetApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  datasetInfoTable: aws_dynamodb.Table;
  datasetItemsTable: aws_dynamodb.Table;
  multiUserTable: aws_dynamodb.Table;
  srcRoot: string;
  commonLayer: aws_lambda.LayerVersion;
  s3Bucket: aws_s3.Bucket;
}

export class GetDatasetApi {
  private readonly src: string;
  private readonly router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly datasetInfoTable: aws_dynamodb.Table;
  private readonly datasetItemsTable: aws_dynamodb.Table;
  private readonly multiUserTable: aws_dynamodb.Table;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly s3Bucket: aws_s3.Bucket;
  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: GetDatasetApiProps) {
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

    const lambdaFunction = this.apiLambda();

    const lambdaIntegration = new aws_apigateway.LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.getResource('{id}')
      ?.addMethod(this.httpMethod, lambdaIntegration, <MethodOptions>{
        apiKeyRequired: true,
        operationName: 'GetDataset',
        methodResponses: [
          ApiModels.methodResponse(this.responseModel(), '200'),
          ApiModels.methodResponses401(),
          ApiModels.methodResponses403(),
          ApiModels.methodResponses404(),
        ],
      });
  }

  private responseModel() {
    return new Model(this.scope, `${this.baseId}-resp-model`, {
      restApi: this.router.api,
      modelName: 'GetDatasetResponse',
      description: `${this.baseId} Response Model`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        type: JsonSchemaType.OBJECT,
        properties: {
          statusCode: {
            type: JsonSchemaType.INTEGER,
            enum: [200],
          },
          debug: SCHEMA_DEBUG,
          data: {
            type: JsonSchemaType.OBJECT,
            properties: {
              dataset_name: {
                type: JsonSchemaType.STRING,
              },
              datasetName: {
                type: JsonSchemaType.STRING,
              },
              prefix: {
                type: JsonSchemaType.STRING,
              },
              s3: {
                type: JsonSchemaType.STRING,
                format: 'uri',
              },
              status: {
                type: JsonSchemaType.STRING,
              },
              timestamp: {
                type: JsonSchemaType.STRING,
              },
              data: {
                type: JsonSchemaType.ARRAY,
                items: {
                  type: JsonSchemaType.OBJECT,
                  properties: {
                    key: {
                      type: JsonSchemaType.STRING,
                    },
                    name: {
                      type: JsonSchemaType.STRING,
                    },
                    type: {
                      type: JsonSchemaType.STRING,
                    },
                    preview_url: {
                      type: JsonSchemaType.STRING,
                      format: 'uri',
                    },
                    dataStatus: {
                      type: JsonSchemaType.STRING,
                    },
                    original_file_name: {
                      type: JsonSchemaType.STRING,
                    },
                  },
                  required: [
                    'key',
                    'name',
                    'type',
                    'preview_url',
                    'dataStatus',
                    'original_file_name',
                  ],
                  additionalProperties: false,
                },
              },
              description: {
                type: JsonSchemaType.STRING,
              },
            },
            required: [
              'dataset_name',
              'datasetName',
              'prefix',
              's3',
              'status',
              'timestamp',
              'data',
              'description',
            ],
            additionalProperties: false,
          },
          message: {
            type: JsonSchemaType.STRING,
            enum: ['OK'],
          },
        },
        required: [
          'statusCode',
          'debug',
          'data',
          'message',
        ],
        additionalProperties: false,
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

  private apiLambda() {
    return new PythonFunction(this.scope, `${this.baseId}-lambda`, {
      entry: `${this.src}/datasets`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'get_dataset.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.iamRole(),
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

