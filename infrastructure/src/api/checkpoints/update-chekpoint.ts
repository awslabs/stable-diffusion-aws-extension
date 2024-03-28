import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, aws_apigateway, aws_dynamodb, aws_iam, aws_lambda, aws_s3, Duration } from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, Model, RequestValidator } from 'aws-cdk-lib/aws-apigateway';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Size } from 'aws-cdk-lib/core';
import { Construct } from 'constructs';


export interface UpdateCheckPointApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  checkpointTable: aws_dynamodb.Table;
  userTable: aws_dynamodb.Table;
  srcRoot: string;
  commonLayer: aws_lambda.LayerVersion;
  s3Bucket: aws_s3.Bucket;
}

export class UpdateCheckPointApi {
  public model: Model;
  public requestValidator: RequestValidator;
  private readonly src: string;
  private readonly router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly checkpointTable: aws_dynamodb.Table;
  private readonly userTable: aws_dynamodb.Table;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly s3Bucket: aws_s3.Bucket;
  private readonly role: aws_iam.Role;
  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: UpdateCheckPointApiProps) {
    this.scope = scope;
    this.src = props.srcRoot;
    this.layer = props.commonLayer;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.checkpointTable = props.checkpointTable;
    this.userTable = props.userTable;
    this.s3Bucket = props.s3Bucket;
    this.role = this.iamRole();
    this.model = this.createModel();
    this.requestValidator = this.createRequestValidator();

    this.updateCheckpointApi();
  }

  private iamRole(): aws_iam.Role {
    const newRole = new aws_iam.Role(this.scope, `${this.baseId}-update-role`, {
      assumedBy: new aws_iam.ServicePrincipal('lambda.amazonaws.com'),
    });

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'dynamodb:BatchGetItem',
        'dynamodb:GetItem',
        'dynamodb:Scan',
        'dynamodb:Query',
        'dynamodb:UpdateItem',
      ],
      resources: [
        this.userTable.tableArn,
        this.checkpointTable.tableArn,
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
        's3:CopyObject',
        's3:DeleteObject',
      ],
      resources: [
        `${this.s3Bucket.bucketArn}/*`,
      ],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        's3:GetObject',
        's3:PutObject',
        's3:DeleteObject',
        's3:ListBucket',
        's3:CopyObject',
        's3:AbortMultipartUpload',
        's3:ListMultipartUploadParts',
        's3:ListBucketMultipartUploads',
      ],
      resources: [`${this.s3Bucket.bucketArn}/*`,
        `arn:${Aws.PARTITION}:s3:::*SageMaker*`,
        `arn:${Aws.PARTITION}:s3:::*Sagemaker*`,
        `arn:${Aws.PARTITION}:s3:::*sagemaker*`],
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
          status: {
            type: JsonSchemaType.STRING,
            minLength: 1,
          },
          name: {
            type: JsonSchemaType.STRING,
            minLength: 1,
            maxLength: 20,
            pattern: '^[A-Za-z][A-Za-z0-9_-]*$',
          },
          multi_parts_tags: {
            type: JsonSchemaType.OBJECT,
          },
        },
      },
      contentType: 'application/json',
    });
  }

  private createRequestValidator(): RequestValidator {
    return new RequestValidator(
      this.scope,
      `${this.baseId}-update-ckpt-validator`,
      {
        restApi: this.router.api,
        validateRequestBody: true,
      });
  }

  private updateCheckpointApi() {

    const renameLambdaFunction = new PythonFunction(this.scope, `${this.baseId}-rename-lambda`, {
      entry: `${this.src}/checkpoints`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'update_checkpoint_rename.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.role,
      memorySize: 10240,
      tracing: aws_lambda.Tracing.ACTIVE,
      ephemeralStorageSize: Size.mebibytes(10240),
      environment: {
        CHECKPOINT_TABLE: this.checkpointTable.tableName,
      },
      layers: [this.layer],
    });

    const lambdaFunction = new PythonFunction(this.scope, `${this.baseId}-lambda`, {
      entry: `${this.src}/checkpoints`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'update_checkpoint.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.role,
      memorySize: 4048,
      tracing: aws_lambda.Tracing.ACTIVE,
      environment: {
        CHECKPOINT_TABLE: this.checkpointTable.tableName,
        RENAME_LAMBDA_NAME: renameLambdaFunction.functionName,
      },
      layers: [this.layer],
    });

    const createModelIntegration = new aws_apigateway.LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.addResource('{id}')
      .addMethod(this.httpMethod, createModelIntegration,
        {
          apiKeyRequired: true,
          requestValidator: this.requestValidator,
          requestModels: {
            'application/json': this.model,
          },
        });
  }
}

