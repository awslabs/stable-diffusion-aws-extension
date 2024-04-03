import { PythonFunction, PythonFunctionProps } from '@aws-cdk/aws-lambda-python-alpha';
import { aws_apigateway, aws_apigateway as apigw, aws_dynamodb, aws_iam, aws_lambda, aws_sqs, Duration } from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, Model, RequestValidator } from 'aws-cdk-lib/aws-apigateway';
import { MethodOptions } from 'aws-cdk-lib/aws-apigateway/lib/method';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { SqsEventSource } from 'aws-cdk-lib/aws-lambda-event-sources';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';


export interface SyncMsgApiProps {
  httpMethod: string;
  router: aws_apigateway.Resource;
  srcRoot: string;
  s3Bucket: s3.Bucket;
  configTable: aws_dynamodb.Table;
  msgTable: aws_dynamodb.Table;
  queue: aws_sqs.Queue;
  commonLayer: aws_lambda.LayerVersion;
}


export class SyncMsgApi {
  private readonly baseId: string;
  private readonly srcRoot: string;
  private readonly router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly s3Bucket: s3.Bucket;
  private readonly configTable: aws_dynamodb.Table;
  private readonly msgTable: aws_dynamodb.Table;
  private readonly queue: aws_sqs.Queue;
  public model: Model;
  public requestValidator: RequestValidator;

  constructor(scope: Construct, id: string, props: SyncMsgApiProps) {
    this.scope = scope;
    this.httpMethod = props.httpMethod;
    this.baseId = id;
    this.router = props.router;
    this.srcRoot = props.srcRoot;
    this.s3Bucket = props.s3Bucket;
    this.configTable = props.configTable;
    this.msgTable = props.msgTable;
    this.layer = props.commonLayer;
    this.queue = props.queue;
    this.model = this.createModel();
    this.requestValidator = this.createRequestValidator();

    this.syncMSGApi();
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
        this.configTable.tableArn,
        this.msgTable.tableArn,
      ],
    }));

    // DynamoDB write permissions
    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'dynamodb:PutItem',
        'dynamodb:UpdateItem',
        'dynamodb:BatchWriteItem',
      ],
      resources: [
        this.configTable.tableArn,
        this.msgTable.tableArn,
      ],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'sqs:ReceiveMessage',
      ],
      resources: [this.queue.queueArn],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        's3:GetObject',
        's3:PutObject',
        's3:DeleteObject',
        's3:ListBucket',
      ],
      resources: [`${this.s3Bucket.bucketArn}/*`],
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

  private apiLambda() {
    return new PythonFunction(this.scope, `${this.baseId}-lambda`, <PythonFunctionProps>{
      entry: `${this.srcRoot}/comfy`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'sync_msg.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.iamRole(),
      memorySize: 2048,
      tracing: aws_lambda.Tracing.ACTIVE,
      environment: {
        MSG_TABLE: this.msgTable.tableName,
        CONFIG_TABLE: this.configTable.tableName,
        SQS_URL: this.queue.queueUrl,
      },
      layers: [this.layer],
    });
  }

  private syncMSGApi() {
    const lambdaFunction = this.apiLambda();

    const syncMsgEventSource = new SqsEventSource(this.queue);
    lambdaFunction.addEventSource(syncMsgEventSource);

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
      operationName: 'SyncMsg',
      methodResponses: [
        ApiModels.methodResponses400(),
        ApiModels.methodResponses401(),
        ApiModels.methodResponses403(),
      ],
    });
  }

  private createModel(): Model {
    return new Model(this.scope, `${this.baseId}-model`, {
      restApi: this.router.api,
      modelName: this.baseId,
      description: `${this.baseId} Request Model`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        title: this.baseId,
        type: JsonSchemaType.OBJECT,
        additionalProperties: true,
      },
      contentType: 'application/json',
    });
  }

  private createRequestValidator() {
    return new RequestValidator(
      this.scope,
      `${this.baseId}-sync-msg-validator`,
      {
        restApi: this.router.api,
        validateRequestBody: true,
      });
  }
}

