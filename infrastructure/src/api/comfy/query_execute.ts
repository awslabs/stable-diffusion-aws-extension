import { PythonFunction, PythonFunctionProps } from '@aws-cdk/aws-lambda-python-alpha';
import { aws_apigateway, aws_dynamodb, aws_iam, aws_lambda, Duration } from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model } from 'aws-cdk-lib/aws-apigateway';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import { SCHEMA_DEBUG, SCHEMA_LAST_KEY, SCHEMA_MESSAGE } from '../../shared/schema';


export interface QueryExecuteApiProps {
  httpMethod: string;
  router: aws_apigateway.Resource;
  s3Bucket: s3.Bucket;
  configTable: aws_dynamodb.Table;
  executeTable: aws_dynamodb.Table;
  commonLayer: aws_lambda.LayerVersion;
}


export class QueryExecuteApi {
  public lambdaIntegration: aws_apigateway.LambdaIntegration;
  private readonly baseId: string;
  private readonly router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly s3Bucket: s3.Bucket;
  private readonly configTable: aws_dynamodb.Table;
  private readonly executeTable: aws_dynamodb.Table;

  constructor(scope: Construct, id: string, props: QueryExecuteApiProps) {
    this.scope = scope;
    this.httpMethod = props.httpMethod;
    this.baseId = id;
    this.router = props.router;
    this.s3Bucket = props.s3Bucket;
    this.configTable = props.configTable;
    this.executeTable = props.executeTable;
    this.layer = props.commonLayer;

    const lambdaFunction = this.apiLambda();

    this.lambdaIntegration = new LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.addMethod(this.httpMethod, this.lambdaIntegration, {
      apiKeyRequired: true,
      operationName: 'ListExecutes',
      requestParameters: {
        'method.request.querystring.limit': false,
        'method.request.querystring.exclusive_start_key': false,
      },
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
      modelName: 'ListExecutesResponse',
      description: `${this.baseId} Response Model`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        type: JsonSchemaType.OBJECT,
        title: 'ListExecutesResponse',
        properties: {
          statusCode: {
            type: JsonSchemaType.INTEGER,
          },
          debug: SCHEMA_DEBUG,
          message: SCHEMA_MESSAGE,
          data: {
            type: JsonSchemaType.OBJECT,
            properties: {
              executes: {
                type: JsonSchemaType.ARRAY,
                items: {
                  type: JsonSchemaType.OBJECT,
                  properties: {
                    prompt_id: {
                      type: JsonSchemaType.STRING,
                    },
                    endpoint_name: {
                      type: JsonSchemaType.STRING,
                    },
                    status: {
                      type: JsonSchemaType.STRING,
                    },
                    create_time: {
                      type: JsonSchemaType.STRING,
                      format: 'date-time',
                    },
                    start_time: {
                      type: JsonSchemaType.STRING,
                      format: 'date-time',
                    },
                    need_sync: {
                      type: JsonSchemaType.BOOLEAN,
                    },
                    output_path: {
                      type: JsonSchemaType.STRING,
                    },
                    output_files: {
                      type: JsonSchemaType.ARRAY,
                    },
                    temp_path: {
                      type: JsonSchemaType.STRING,
                    },
                    temp_files: {
                      type: JsonSchemaType.ARRAY,
                    },
                  },
                  required: [
                    'prompt_id',
                    'endpoint_name',
                    'status',
                    'create_time',
                    'start_time',
                    'need_sync',
                  ],
                },
              },
              last_evaluated_key: SCHEMA_LAST_KEY,
            },
            required: [
              'executes',
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

  private apiLambda() {
    return new PythonFunction(this.scope, `${this.baseId}-lambda`, <PythonFunctionProps>{
      entry: '../middleware_api/comfy',
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'query_execute.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.iamRole(),
      memorySize: 2048,
      tracing: aws_lambda.Tracing.ACTIVE,
      environment: {
        EXECUTE_TABLE: this.executeTable.tableName,
        CONFIG_TABLE: this.configTable.tableName,
      },
      layers: [this.layer],
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
        this.configTable.tableArn,
        this.executeTable.tableArn,
      ],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        's3:GetObject',
        's3:PutObject',
        's3:DeleteObject',
        's3:ListBucket',
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

}

