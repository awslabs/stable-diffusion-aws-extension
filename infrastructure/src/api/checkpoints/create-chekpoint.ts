import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, aws_apigateway, aws_dynamodb, aws_iam, aws_lambda, aws_s3, Duration } from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, Model, RequestValidator } from 'aws-cdk-lib/aws-apigateway';
import { MethodOptions } from 'aws-cdk-lib/aws-apigateway/lib/method';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Size } from 'aws-cdk-lib/core';
import { Construct } from 'constructs';


export interface CreateCheckPointApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  checkpointTable: aws_dynamodb.Table;
  multiUserTable: aws_dynamodb.Table;
  srcRoot: string;
  commonLayer: aws_lambda.LayerVersion;
  s3Bucket: aws_s3.Bucket;
}

export class CreateCheckPointApi {
  public model: Model;
  public requestValidator: RequestValidator;
  private readonly src: string;
  private readonly router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly checkpointTable: aws_dynamodb.Table;
  private readonly multiUserTable: aws_dynamodb.Table;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly s3Bucket: aws_s3.Bucket;
  private readonly uploadByUrlLambda: PythonFunction;
  private readonly role: aws_iam.Role;
  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: CreateCheckPointApiProps) {
    this.scope = scope;
    this.httpMethod = props.httpMethod;
    this.checkpointTable = props.checkpointTable;
    this.multiUserTable = props.multiUserTable;
    this.baseId = id;
    this.router = props.router;
    this.src = props.srcRoot;
    this.layer = props.commonLayer;
    this.s3Bucket = props.s3Bucket;
    this.role = this.iamRole();
    this.model = this.createModel();
    this.requestValidator = this.createRequestValidator();
    this.uploadByUrlLambda = this.uploadByUrlLambdaFunction();
    this.createCheckpointApi();
  }

  private uploadByUrlLambdaFunction() {
    return new PythonFunction(this.scope, `${this.baseId}-url-lambda`, {
      functionName: `${this.baseId}-create-checkpoint-by-url`,
      entry: `${this.src}/checkpoints`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'update_checkpoint_by_url.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.role,
      memorySize: 3070,
      tracing: aws_lambda.Tracing.ACTIVE,
      ephemeralStorageSize: Size.mebibytes(10240),
      environment: {
        CHECKPOINT_TABLE: this.checkpointTable.tableName,
      },
      layers: [this.layer],
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
      resources: [this.checkpointTable.tableArn, this.multiUserTable.tableArn],
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

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'lambda:invokeFunction',
      ],
      resources: [
        `arn:${Aws.PARTITION}:lambda:${Aws.REGION}:${Aws.ACCOUNT_ID}:function:*${this.baseId}*`,
      ],
    }));

    return newRole;
  }

  private createModel(): Model {
    return new Model(this.scope, `${this.baseId}-model`, {
      restApi: this.router.api,
      modelName: this.baseId,
      description: `${this.baseId} Request Model`,
      schema: {
        schema: JsonSchemaVersion.DRAFT4,
        title: this.baseId,
        type: JsonSchemaType.OBJECT,
        properties: {
          checkpoint_type: {
            type: JsonSchemaType.STRING,
            enum: [
              'Stable-diffusion',
              'embeddings',
              'Lora',
              'hypernetworks',
              'ControlNet',
              'VAE',
            ],
          },
          filenames: {
            type: JsonSchemaType.ARRAY,
            items: {
              type: JsonSchemaType.OBJECT,
              properties: {
                filename: {
                  type: JsonSchemaType.STRING,
                  minLength: 1,
                },
                parts_number: {
                  type: JsonSchemaType.INTEGER,
                  minimum: 1,
                  maximum: 100,
                },
              },
            },
            minItems: 1,
            maxItems: 20,
          },
          urls: {
            type: JsonSchemaType.ARRAY,
            items: {
              type: JsonSchemaType.STRING,
              minLength: 1,
            },
            minItems: 1,
            maxItems: 20,
          },
          params: {
            type: JsonSchemaType.OBJECT,
            properties: {
              message: {
                type: JsonSchemaType.STRING,
              },
              creator: {
                type: JsonSchemaType.STRING,
              },
            },
          },
        },
        required: [
          'checkpoint_type',
        ],
      },
      contentType: 'application/json',
    });
  }

  private createRequestValidator(): RequestValidator {
    return new RequestValidator(
      this.scope,
      `${this.baseId}-create-ckpt-validator`,
      {
        restApi: this.router.api,
        validateRequestBody: true,
      });
  }

  private createCheckpointApi() {
    const lambdaFunction = new PythonFunction(this.scope, `${this.baseId}-lambda`, {
      entry: `${this.src}/checkpoints`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'create_checkpoint.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.role,
      memorySize: 3070,
      tracing: aws_lambda.Tracing.ACTIVE,
      environment: {
        CHECKPOINT_TABLE: this.checkpointTable.tableName,
        UPLOAD_BY_URL_LAMBDA_NAME: this.uploadByUrlLambda.functionName,
      },
      layers: [this.layer],
    });

    const createCheckpointIntegration = new aws_apigateway.LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.addMethod(this.httpMethod, createCheckpointIntegration, <MethodOptions>{
      apiKeyRequired: true,
      requestValidator: this.requestValidator,
      requestModels: {
        'application/json': this.model,
      },
    });
  }
}

