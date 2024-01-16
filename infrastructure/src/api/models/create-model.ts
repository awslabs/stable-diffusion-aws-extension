import { PythonFunction, PythonFunctionProps } from '@aws-cdk/aws-lambda-python-alpha';
import {
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


export interface CreateModelJobApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  modelTable: aws_dynamodb.Table;
  checkpointTable: aws_dynamodb.Table;
  multiUserTable: aws_dynamodb.Table;
  srcRoot: string;
  s3Bucket: aws_s3.Bucket;
  commonLayer: aws_lambda.LayerVersion;
  logLevel: CfnParameter;
}

export class CreateModelJobApi {
  private readonly src;
  private readonly router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly modelTable: aws_dynamodb.Table;
  private readonly checkpointTable: aws_dynamodb.Table;
  private readonly multiUserTable: aws_dynamodb.Table;
  private readonly s3Bucket: aws_s3.Bucket;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly logLevel: CfnParameter;
  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: CreateModelJobApiProps) {
    this.scope = scope;
    this.router = props.router;
    this.baseId = id;
    this.httpMethod = props.httpMethod;
    this.modelTable = props.modelTable;
    this.src = props.srcRoot;
    this.s3Bucket = props.s3Bucket;
    this.layer = props.commonLayer;
    this.checkpointTable = props.checkpointTable;
    this.multiUserTable = props.multiUserTable;
    this.logLevel = props.logLevel;

    this.createModelJobApi();
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
        this.modelTable.tableArn,
        this.checkpointTable.tableArn,
        this.multiUserTable.tableArn,
      ],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        's3:GetObject',
        's3:PutObject',
        's3:AbortMultipartUpload',
        's3:ListMultipartUploadParts',
        's3:ListBucketMultipartUploads',
      ],
      resources: [`${this.s3Bucket.bucketArn}/*`],
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

  private createModelJobApi() {
    const lambdaFunction = new PythonFunction(this.scope, `${this.baseId}-lambda`, <PythonFunctionProps>{
      entry: `${this.src}/models`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_9,
      index: 'create_model.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.iamRole(),
      memorySize: 1024,
      environment: {
        DYNAMODB_TABLE: this.modelTable.tableName,
        S3_BUCKET: this.s3Bucket.bucketName,
        CHECKPOINT_TABLE: this.checkpointTable.tableName,
        MULTI_USER_TABLE: this.multiUserTable.tableName,
        LOG_LEVEL: this.logLevel.valueAsString,
      },
      layers: [this.layer],
    });
    const createModelIntegration = new apigw.LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    const requestModel = new Model(this.scope, `${this.baseId}-model`, {
      restApi: this.router.api,
      modelName: this.baseId,
      description: `${this.baseId} Request Model`,
      schema: {
        schema: JsonSchemaVersion.DRAFT4,
        title: this.baseId,
        type: JsonSchemaType.OBJECT,
        properties: {
          model_type: {
            type: JsonSchemaType.STRING,
            minLength: 1,
          },
          name: {
            type: JsonSchemaType.STRING,
            minLength: 1,
          },
          filenames: {
            type: JsonSchemaType.ARRAY,
            items: {
              type: JsonSchemaType.OBJECT,
            },
          },
          params: {
            type: JsonSchemaType.OBJECT,
          },
        },
        required: [
          'model_type',
          'name',
          'filenames',
          'params',
        ],
      },
      contentType: 'application/json',
    });

    const requestValidator = new RequestValidator(
      this.scope,
      `${this.baseId}-validator`,
      {
        restApi: this.router.api,
        validateRequestBody: true,
      });

    this.router.addMethod(this.httpMethod, createModelIntegration, <MethodOptions>{
      apiKeyRequired: true,
      requestValidator,
      requestModels: {
        'application/json': requestModel,
      },
    });
  }

}

