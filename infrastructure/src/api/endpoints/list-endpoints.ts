import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { aws_apigateway, aws_dynamodb, aws_iam, aws_lambda, Duration } from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model } from 'aws-cdk-lib/aws-apigateway';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import { SCHEMA_DEBUG, SCHEMA_LAST_KEY, SCHEMA_MESSAGE } from '../../shared/schema';


export interface ListEndpointsApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  endpointDeploymentTable: aws_dynamodb.Table;
  multiUserTable: aws_dynamodb.Table;
  commonLayer: aws_lambda.LayerVersion;
}

export class ListEndpointsApi {
  private readonly router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly endpointDeploymentTable: aws_dynamodb.Table;
  private readonly multiUserTable: aws_dynamodb.Table;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly baseId: string;


  constructor(scope: Construct, id: string, props: ListEndpointsApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.endpointDeploymentTable = props.endpointDeploymentTable;
    this.multiUserTable = props.multiUserTable;
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
      operationName: 'ListEndpoints',
      requestParameters: {
        'method.request.querystring.limit': false,
      },
      methodResponses: [
        ApiModels.methodResponse(this.responseModel()),
        ApiModels.methodResponses401(),
        ApiModels.methodResponses403(),
      ],
    });
  }

  private responseModel() {
    return new Model(this.scope, `${this.baseId}-resp-model`, {
      restApi: this.router.api,
      modelName: 'ListEndpointsResponse',
      description: `${this.baseId} Response Model`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        type: JsonSchemaType.OBJECT,
        title: 'ListEndpointsResponse',
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
              endpoints: {
                type: JsonSchemaType.ARRAY,
                items: {
                  type: JsonSchemaType.OBJECT,
                  properties: {
                    EndpointDeploymentJobId: {
                      type: JsonSchemaType.STRING,
                      pattern: '^[a-f0-9\\-]{36}$',
                    },
                    autoscaling: {
                      type: JsonSchemaType.BOOLEAN,
                    },
                    max_instance_number: {
                      type: JsonSchemaType.STRING,
                      pattern: '^[0-9]+$',
                    },
                    startTime: {
                      type: JsonSchemaType.STRING,
                      format: 'date-time',
                    },
                    instance_type: {
                      type: JsonSchemaType.STRING,
                    },
                    current_instance_count: {
                      type: JsonSchemaType.STRING,
                      pattern: '^[0-9]+$',
                    },
                    endpoint_status: {
                      type: JsonSchemaType.STRING,
                    },
                    endpoint_name: {
                      type: JsonSchemaType.STRING,
                    },
                    endpoint_type: {
                      type: JsonSchemaType.STRING,
                    },
                    owner_group_or_role: {
                      type: JsonSchemaType.ARRAY,
                      items: {
                        type: JsonSchemaType.STRING,
                      },
                    },
                    min_instance_number: {
                      type: JsonSchemaType.STRING,
                      pattern: '^[0-9]+$',
                    },
                    custom_extensions: {
                      type: JsonSchemaType.STRING,
                    },
                    service_type: {
                      type: JsonSchemaType.STRING,
                    },
                  },
                  required: [
                    'EndpointDeploymentJobId',
                    'autoscaling',
                    'max_instance_number',
                    'startTime',
                    'instance_type',
                    'current_instance_count',
                    'endpoint_status',
                    'endpoint_name',
                    'endpoint_type',
                    'owner_group_or_role',
                    'min_instance_number',
                    'service_type',
                  ],
                  additionalProperties: true,
                },
              },
              last_evaluated_key: SCHEMA_LAST_KEY,
            },
            required: [
              'endpoints',
              'last_evaluated_key',
            ],
            additionalProperties: false,
          },
        },
        required: [
          'statusCode',
          'debug',
          'data',
          'message',
        ],
        additionalProperties: false,
      }
      ,
      contentType: 'application/json',
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
      resources: [
        this.endpointDeploymentTable.tableArn,
        this.multiUserTable.tableArn,
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

  private apiLambda() {
    return new PythonFunction(this.scope, `${this.baseId}-lambda`, {
      entry: '../middleware_api/endpoints',
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'list_endpoints.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.iamRole(),
      memorySize: 2048,
      tracing: aws_lambda.Tracing.ACTIVE,
      layers: [this.layer],
    });
  }

}

