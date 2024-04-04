import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { aws_apigateway, aws_dynamodb, aws_iam, aws_kms, aws_lambda, Duration } from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model, RequestValidator } from 'aws-cdk-lib/aws-apigateway';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import { SCHEMA_DEBUG, SCHEMA_MESSAGE, SCHEMA_PASSWORD, SCHEMA_USER_ROLES, SCHEMA_USERNAME } from '../../shared/schema';

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
  private readonly multiUserTable: aws_dynamodb.Table;
  private readonly passwordKey: aws_kms.IKey;
  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: CreateUserApiProps) {
    this.scope = scope;
    this.httpMethod = props.httpMethod;
    this.baseId = id;
    this.passwordKey = props.passwordKey;
    this.router = props.router;
    this.layer = props.commonLayer;
    this.multiUserTable = props.multiUserTable;

    const lambdaFunction = this.apiLambda();

    const lambdaIntegration = new LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.addMethod(this.httpMethod, lambdaIntegration, {
      apiKeyRequired: true,
      requestValidator: this.createRequestValidator(),
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
        this.multiUserTable.tableArn,
      ],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'kms:Encrypt',
        'kms:Decrypt',
      ],
      resources: ['*'],
      conditions: {
        StringEquals: {
          'kms:RequestAlias': `alias/${this.passwordKey.keyId}`,
        },
      },
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

  private createRequestBodyModel(): Model {
    return new Model(this.scope, `${this.baseId}-model`, {
      restApi: this.router.api,
      modelName: this.baseId,
      description: `${this.baseId} Request Model`,
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

  private createRequestValidator(): RequestValidator {
    return new RequestValidator(
      this.scope,
      `${this.baseId}-create-user-validator`,
      {
        restApi: this.router.api,
        validateRequestBody: true,
      });
  }

  private responseModel() {
    return new Model(this.scope, `${this.baseId}-resp-model`, {
      restApi: this.router.api,
      modelName: 'CreateUserResponse',
      description: 'CreateUser Response Model',
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
    return new PythonFunction(this.scope, `${this.baseId}-lambda`, {
      entry: '../middleware_api/users',
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'create_user.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.iamRole(),
      memorySize: 2048,
      tracing: aws_lambda.Tracing.ACTIVE,
      environment: {
        KEY_ID: `alias/${this.passwordKey.keyId}`,
      },
      layers: [this.layer],
    });
  }

}

