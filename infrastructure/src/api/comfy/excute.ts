import { PythonFunction, PythonFunctionProps } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, aws_apigateway, aws_apigateway as apigw, aws_dynamodb, aws_iam, aws_lambda, Duration } from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, Model, RequestValidator } from 'aws-cdk-lib/aws-apigateway';
import { MethodOptions } from 'aws-cdk-lib/aws-apigateway/lib/method';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Size } from 'aws-cdk-lib/core';
import { Construct } from 'constructs';


export interface ExecuteApiProps {
  httpMethod: string;
  router: aws_apigateway.Resource;
  srcRoot: string;
  configTable: aws_dynamodb.Table;
  executeTable: aws_dynamodb.Table;
  endpointTable: aws_dynamodb.Table;
  commonLayer: aws_lambda.LayerVersion;
}

export class ExecuteApi {
  private readonly baseId: string;
  private readonly srcRoot: string;
  private readonly router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly configTable: aws_dynamodb.Table;
  private readonly executeTable: aws_dynamodb.Table;
  private readonly endpointTable: aws_dynamodb.Table;
  public model: Model;
  public requestValidator: RequestValidator;

  constructor(scope: Construct, id: string, props: ExecuteApiProps) {
    this.scope = scope;
    this.httpMethod = props.httpMethod;
    this.baseId = id;
    this.router = props.router;
    this.srcRoot = props.srcRoot;
    this.configTable = props.configTable;
    this.executeTable = props.executeTable;
    this.endpointTable = props.endpointTable;
    this.layer = props.commonLayer;
    this.model = this.createModel();
    this.requestValidator = this.createRequestValidator();

    this.executeApi();
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
        'dynamodb:Query',
      ],
      resources: [
        this.configTable.tableArn,
        this.executeTable.tableArn,
        `${this.endpointTable.tableArn}`,
        `${this.endpointTable.tableArn}/*`,
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
        '*',
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

  private executeApi() {
    const lambdaFunction = new PythonFunction(this.scope, `${this.baseId}-lambda`, <PythonFunctionProps>{
      entry: `${this.srcRoot}/comfy`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'execute.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.iamRole(),
      memorySize: 3070,
      tracing: aws_lambda.Tracing.ACTIVE,
      ephemeralStorageSize: Size.gibibytes(10),
      environment: {
        EXECUTE_TABLE: this.executeTable.tableName,
        CONFIG_TABLE: this.configTable.tableName,
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
          prompt_id: {
            type: JsonSchemaType.STRING,
            minLength: 1,
          },
          prompt: {
            type: JsonSchemaType.OBJECT,
            minItems: 1,
            additionalProperties: true,
          },
          endpoint_name: {
            type: JsonSchemaType.STRING,
            minLength: 1,
          },
          inference_type: {
            type: JsonSchemaType.STRING,
            minLength: 1,
          },
          need_sync: {
            type: JsonSchemaType.BOOLEAN,
            minLength: 1,
          },
          number: {
            type: JsonSchemaType.STRING,
            minLength: 1,
          },
          front: {
            type: JsonSchemaType.BOOLEAN,
            minLength: 1,
          },
          extra_data: {
            type: JsonSchemaType.OBJECT,
            minLength: 1,
            additionalProperties: true,
          },
          client_id: {
            type: JsonSchemaType.STRING,
            minLength: 1,
          },
        },
        required: [
          'prompt_id',
          'prompt',
          'need_sync',
          'inference_type',
          'endpoint_name',
        ],
      },
      contentType: 'application/json',
    });
  }

  private createRequestValidator() {
    return new RequestValidator(
      this.scope,
      `${this.baseId}-execute-validator`,
      {
        restApi: this.router.api,
        validateRequestBody: true,
      });
  }
}

