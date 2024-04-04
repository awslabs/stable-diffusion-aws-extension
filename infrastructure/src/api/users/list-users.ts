import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { aws_apigateway, aws_dynamodb, aws_iam, aws_kms, aws_lambda, Duration } from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model } from 'aws-cdk-lib/aws-apigateway';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import { SCHEMA_DEBUG, SCHEMA_LAST_KEY, SCHEMA_MESSAGE } from '../../shared/schema';


export interface ListUsersApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  multiUserTable: aws_dynamodb.Table;
  commonLayer: aws_lambda.LayerVersion;
  passwordKey: aws_kms.IKey;
}

export class ListUsersApi {
  private readonly router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly multiUserTable: aws_dynamodb.Table;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly passwordKey: aws_kms.IKey;
  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: ListUsersApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.passwordKey = props.passwordKey;
    this.httpMethod = props.httpMethod;
    this.multiUserTable = props.multiUserTable;
    this.layer = props.commonLayer;

    const lambdaFunction = this.apiLambda();

    const integration = new LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.addMethod(this.httpMethod, integration, {
      apiKeyRequired: true,
      operationName: 'ListUsers',
      methodResponses: [
        ApiModels.methodResponse(this.responseModel()),
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
      ],
      resources: [this.multiUserTable.tableArn],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
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
        'kms:Decrypt',
      ],
      resources: ['*'],
    }));
    return newRole;
  }

  private responseModel() {
    return new Model(this.scope, `${this.baseId}-resp-model`, {
      restApi: this.router.api,
      modelName: 'ListUsersResponse',
      description: 'ListUsers Response Model',
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        title: this.baseId,
        type: JsonSchemaType.OBJECT,
        properties: {
          statusCode: {
            type: JsonSchemaType.INTEGER,
            enum: [200],
          },
          debug: SCHEMA_DEBUG,
          message: SCHEMA_MESSAGE,
          data: {
            type: JsonSchemaType.OBJECT,
            properties: {
              users: {
                type: JsonSchemaType.ARRAY,
                items: {
                  type: JsonSchemaType.OBJECT,
                  properties: {
                    username: {
                      type: JsonSchemaType.STRING,
                    },
                    roles: {
                      type: JsonSchemaType.ARRAY,
                      items: {
                        type: JsonSchemaType.STRING,
                      },
                    },
                    creator: {
                      type: JsonSchemaType.STRING,
                    },
                    permissions: {
                      type: JsonSchemaType.ARRAY,
                      items: {
                        type: JsonSchemaType.STRING,
                      },
                    },
                    password: {
                      type: JsonSchemaType.STRING,
                    },
                  },
                  required: [
                    'creator',
                    'password',
                    'permissions',
                    'roles',
                    'username',
                  ],
                  additionalProperties: false,
                },
              },
              last_evaluated_key: SCHEMA_LAST_KEY,
            },
            required: [
              'users',
            ],
            additionalProperties: false,
          },
        },
        required: [
          'data',
          'debug',
          'message',
          'statusCode',
        ],
        additionalProperties: false,
      },
      contentType: 'application/json',
    });
  }

  private apiLambda() {
    return new PythonFunction(this.scope, `${this.baseId}-lambda`, {
      entry: '../middleware_api/users',
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'list_users.py',
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

