import { PythonFunction, PythonFunctionProps } from '@aws-cdk/aws-lambda-python-alpha';
import {
  Aws,
  aws_apigateway,
  aws_apigateway as apigw,
  aws_dynamodb,
  aws_iam,
  aws_lambda,
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
}

export class PrepareApi {
  private readonly baseId: string;
  private readonly srcRoot: string;
  private readonly router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly s3Bucket: s3.Bucket;
  private readonly configTable: aws_dynamodb.Table;
  private readonly syncTable: aws_dynamodb.Table;
  private readonly instanceMonitorTable: aws_dynamodb.Table;
  private readonly endpointTable: aws_dynamodb.Table;
  public model: Model;
  public requestValidator: RequestValidator;

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
    this.model = this.createModel();
    this.requestValidator = this.createRequestValidator();

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
      },
      layers: [this.layer],
    });

    const lambdaIntegration = new apigw.LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.addMethod(this.httpMethod, lambdaIntegration, <MethodOptions>{
      apiKeyRequired: true,
      requestValidator: this.requestValidator,
      requestModels: {
        'application/json': this.model,
      },
    });
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
          prepare_id: {
            type: JsonSchemaType.STRING,
          },
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
  }

  private createRequestValidator() {
    return new RequestValidator(
      this.scope,
      `${this.baseId}-prepare-validator`,
      {
        restApi: this.router.api,
        validateRequestBody: true,
      });
  }
}

