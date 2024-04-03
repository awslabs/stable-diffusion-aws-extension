import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, aws_lambda, Duration } from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model, Resource } from 'aws-cdk-lib/aws-apigateway';
import { Effect, PolicyStatement, Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';
import { Architecture, LayerVersion, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';

export interface PingApiProps {
  router: Resource;
  httpMethod: string;
  srcRoot: string;
  commonLayer: LayerVersion;
}

export class PingApi {
  private readonly src: string;
  private readonly router: Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly layer: LayerVersion;
  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: PingApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.src = props.srcRoot;
    this.layer = props.commonLayer;

    this.pingApi();
  }

  private iamRole(): Role {

    const newRole = new Role(
      this.scope,
      `${this.baseId}-role`,
      {
        assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
      },
    );

    newRole.addToPolicy(new PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'logs:CreateLogGroup',
        'logs:CreateLogStream',
        'logs:PutLogEvents',
      ],
      resources: [`arn:${Aws.PARTITION}:logs:${Aws.REGION}:${Aws.ACCOUNT_ID}:log-group:*:*`],
    }));

    return newRole;
  }

  private pingApi() {

    const lambdaFunction = new PythonFunction(
      this.scope,
      `${this.baseId}-lambda`,
      {
        entry: `${this.src}/service`,
        architecture: Architecture.X86_64,
        runtime: Runtime.PYTHON_3_10,
        index: 'ping.py',
        handler: 'handler',
        timeout: Duration.seconds(900),
        role: this.iamRole(),
        memorySize: 2048,
        tracing: aws_lambda.Tracing.ACTIVE,
        layers: [this.layer],
      });

    const lambdaIntegration = new LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    const responseModel = new Model(this.scope, `${this.baseId}-resp-model`, {
      restApi: this.router.api,
      modelName: this.baseId,
      description: `${this.baseId} Response Model`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        type: JsonSchemaType.OBJECT,
        properties: {
          statusCode: {
            type: JsonSchemaType.INTEGER,
            enum: [200],
          },
          debug: {
            type: JsonSchemaType.OBJECT,
            properties: {
              function_url: {
                type: JsonSchemaType.STRING,
                format: 'uri',
              },
              log_url: {
                type: JsonSchemaType.STRING,
                format: 'uri',
              },
              trace_url: {
                type: JsonSchemaType.STRING,
                format: 'uri',
              },
            },
            required: [
              'function_url',
              'log_url',
              'trace_url',
            ],
            additionalProperties: false,
          },
          message: {
            type: JsonSchemaType.STRING,
            enum: ['pong'],
          },
        },
        required: [
          'statusCode',
          'debug',
          'message',
        ],
        additionalProperties: false,
      }
      ,
      contentType: 'application/json',
    });

    this.router.addMethod(
      this.httpMethod,
      lambdaIntegration,
      {
        apiKeyRequired: true,
        operationName: 'ServicePing',
        methodResponses: [{
          statusCode: '200',
          responseModels: {
            'application/json': responseModel,
          },
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': true,
          },
        }],
      });

  }
}
