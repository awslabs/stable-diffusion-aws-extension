import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import {aws_apigateway, aws_dynamodb, aws_kms, aws_lambda, Duration} from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model } from 'aws-cdk-lib/aws-apigateway';
import {Role} from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import { SCHEMA_DEBUG, SCHEMA_MESSAGE, SCHEMA_PASSWORD, SCHEMA_USER_ROLES, SCHEMA_USERNAME } from '../../shared/schema';
import { ApiValidators } from '../../shared/validator';
import {ESD_ROLE} from "../../shared/const";

export interface CreateUserApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  multiUserTable: aws_dynamodb.Table;
  commonLayer: aws_lambda.LayerVersion;
  passwordKey: aws_kms.IKey;
}

export class CreateUserApi {
  private readonly router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly passwordKey: aws_kms.IKey;
  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: CreateUserApiProps) {
    this.scope = scope;
    this.httpMethod = props.httpMethod;
    this.baseId = id;
    this.passwordKey = props.passwordKey;
    this.router = props.router;
    this.layer = props.commonLayer;

    const lambdaFunction = this.apiLambda();

    const lambdaIntegration = new LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.addMethod(this.httpMethod, lambdaIntegration, {
      apiKeyRequired: true,
      requestValidator: ApiValidators.bodyValidator,
      requestModels: {
        'application/json': this.createRequestBodyModel(),
      },
      operationName: 'CreateUser',
      methodResponses: [
        ApiModels.methodResponse(this.responseModel(), '201'),
        ApiModels.methodResponses400(),
        ApiModels.methodResponses401(),
        ApiModels.methodResponses403(),
        ApiModels.methodResponses404(),
      ],
    });
  }

  private createRequestBodyModel(): Model {
    return new Model(this.scope, `${this.baseId}-model`, {
      restApi: this.router.api,
      modelName: `${this.baseId}Request`,
      description: `Request Model ${this.baseId}`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        title: this.baseId,
        type: JsonSchemaType.OBJECT,
        properties: {
          username: SCHEMA_USERNAME,
          password: SCHEMA_PASSWORD,
          roles: SCHEMA_USER_ROLES,
        },
        required: [
          'username',
        ],
      },
      contentType: 'application/json',
    });
  }

  private responseModel() {
    return new Model(this.scope, `${this.baseId}-resp-model`, {
      restApi: this.router.api,
      modelName: 'CreateUserResponse',
      description: 'Response Model CreateUserResponse',
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        title: this.baseId,
        type: JsonSchemaType.OBJECT,
        properties: {
          statusCode: {
            type: JsonSchemaType.INTEGER,
          },
          debug: SCHEMA_DEBUG,
          message: SCHEMA_MESSAGE,
        },
        required: [
          'debug',
          'message',
          'statusCode',
        ],
      },
      contentType: 'application/json',
    });
  }

  private apiLambda() {
    const role = <Role>Role.fromRoleName(this.scope, `${this.baseId}-role`, ESD_ROLE);

    return new PythonFunction(this.scope, `${this.baseId}-lambda`, {
      entry: '../middleware_api/users',
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'create_user.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: role,
      memorySize: 2048,
      tracing: aws_lambda.Tracing.ACTIVE,
      environment: {
        KEY_ID: `alias/${this.passwordKey.keyId}`,
      },
      layers: [this.layer],
    });
  }

}

