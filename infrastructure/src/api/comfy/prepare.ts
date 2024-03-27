import { PythonFunction, PythonFunctionProps } from '@aws-cdk/aws-lambda-python-alpha';
import {
  Aws,
  aws_apigateway,
  aws_apigateway as apigw,
  aws_dynamodb,
  aws_iam,
  aws_lambda,
  CfnParameter,
  Duration,
} from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, Model, RequestValidator } from 'aws-cdk-lib/aws-apigateway';
import { MethodOptions } from 'aws-cdk-lib/aws-apigateway/lib/method';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';


export interface PrepareApiProps {
  httpMethod: string;
  router: aws_apigateway.Resource;
  srcRoot: string;
  s3Bucket: s3.Bucket;
  configTable: aws_dynamodb.Table;
  syncTable: aws_dynamodb.Table;
  instanceMonitorTable: aws_dynamodb.Table;
  endpointTable: aws_dynamodb.Table;
  commonLayer: aws_lambda.LayerVersion;
  logLevel: CfnParameter;
}

export class PrepareApi {
  private readonly baseId: string;
  private readonly srcRoot: string;
  private readonly router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly logLevel: CfnParameter;
  private readonly s3Bucket: s3.Bucket;
  private readonly configTable: aws_dynamodb.Table;
  private readonly syncTable: aws_dynamodb.Table;
  private readonly instanceMonitorTable: aws_dynamodb.Table;
  private readonly endpointTable: aws_dynamodb.Table;

  constructor(scope: Construct, id: string, props: PrepareApiProps) {
    this.scope = scope;
    this.httpMethod = props.httpMethod;
    this.baseId = id;
    this.router = props.router;
    this.srcRoot = props.srcRoot;
    this.s3Bucket = props.s3Bucket;
    this.configTable = props.configTable;
    this.syncTable = props.syncTable;
    this.instanceMonitorTable = props.instanceMonitorTable;
    this.endpointTable = props.endpointTable;
    this.layer = props.commonLayer;
    this.logLevel = props.logLevel;

    this.prepareApi();
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
        this.configTable.tableArn,
        this.syncTable.tableArn,
        this.instanceMonitorTable.tableArn,
        this.endpointTable.tableArn,
      ],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'sagemaker:InvokeEndpointAsync',
        'sagemaker:InvokeEndpoint',
      ],
      resources: [`arn:${Aws.PARTITION}:sagemaker:${Aws.REGION}:${Aws.ACCOUNT_ID}:endpoint/*`],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        's3:GetObject',
        's3:PutObject',
        's3:DeleteObject',
        's3:ListBucket',
        's3:CreateBucket',
      ],
      resources: [
        `${this.s3Bucket.bucketArn}/*`,
        `${this.s3Bucket.bucketArn}`,
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

  private prepareApi() {
    const lambdaFunction = new PythonFunction(this.scope, `${this.baseId}-lambda`, <PythonFunctionProps>{
      entry: `${this.srcRoot}/comfy`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'prepare.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.iamRole(),
      memorySize: 2048,
      tracing: aws_lambda.Tracing.ACTIVE,
      environment: {
        SYNC_TABLE: this.syncTable.tableName,
        CONFIG_TABLE: this.configTable.tableName,
        INSTANCE_MONITOR_TABLE: this.instanceMonitorTable.tableName,
        ENDPOINT_TABLE: this.endpointTable.tableName,
        BUCKET_NAME: this.s3Bucket.bucketName,
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
          endpoint_name: {
            type: JsonSchemaType.STRING,
            minLength: 1,
          },
          s3_source_path: {
            type: JsonSchemaType.STRING,
            minLength: 1,
          },
          local_target_path: {
            type: JsonSchemaType.STRING,
            minLength: 1,
          },
          prepare_type: {
            type: JsonSchemaType.STRING,
            enum: ['default', 'inputs', 'nodes', 'models', 'custom'],
          },
          need_reboot: {
            type: JsonSchemaType.BOOLEAN,
          },
        },
        required: [
          'endpoint_name',
          'need_reboot',
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

    const lambdaIntegration = new apigw.LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );
    this.router.addMethod(this.httpMethod, lambdaIntegration, <MethodOptions>{
      apiKeyRequired: true,
      requestValidator,
      requestModels: {
        'application/json': requestModel,
      },
    });
  }
}

