import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import {Aws, aws_lambda, Duration} from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model, Resource } from 'aws-cdk-lib/aws-apigateway';
import { Role } from 'aws-cdk-lib/aws-iam';
import { Architecture, LayerVersion, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import { SCHEMA_DEBUG, SCHEMA_MESSAGE } from '../../shared/schema';
import {ESD_ROLE} from "../../shared/const";

export interface PingApiProps {
  router: Resource;
  httpMethod: string;
  commonLayer: LayerVersion;
}

export class PingApi {
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
    this.layer = props.commonLayer;

    const lambdaFunction = this.apiLambda();

    const lambdaIntegration = new LambdaIntegration(lambdaFunction, { proxy: true });

    this.router.addMethod(
      this.httpMethod,
      lambdaIntegration,
      {
        apiKeyRequired: true,
        operationName: 'Ping',
        methodResponses: [
          ApiModels.methodResponse(this.responseModel()),
          ApiModels.methodResponses400(),
          ApiModels.methodResponses401(),
          ApiModels.methodResponses403(),
        ],
      });
  }

  private responseModel() {
    return new Model(this.scope, `${this.baseId}-resp-model`, {
      restApi: this.router.api,
      modelName: 'PingResponse',
      description: `Response Model ${this.baseId}`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        title: 'PingResponse',
        type: JsonSchemaType.OBJECT,
        description: 'Response Model for Ping API',
        properties: {
          statusCode: {
            type: JsonSchemaType.INTEGER,
            enum: [200],
          },
          debug: SCHEMA_DEBUG,
          message: SCHEMA_MESSAGE,
        },
        required: [
          'statusCode',
          'debug',
          'message',
        ],
      },
      contentType: 'application/json',
    });
  }

  private apiLambda() {

    const role = <Role>Role.fromRoleName(this.scope, `${this.baseId}-role`, `${ESD_ROLE}-${Aws.REGION}`);

    return new PythonFunction(this.scope,
      `${this.baseId}-lambda`,
      {
        entry: '../middleware_api/service',
        architecture: Architecture.X86_64,
        runtime: Runtime.PYTHON_3_10,
        index: 'ping.py',
        handler: 'handler',
        timeout: Duration.seconds(900),
        role: role,
        memorySize: 2048,
        tracing: aws_lambda.Tracing.ACTIVE,
        layers: [this.layer],
      });
  }
}
