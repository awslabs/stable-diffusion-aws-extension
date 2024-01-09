import { PythonFunction, PythonFunctionProps } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, CfnParameter, Duration } from 'aws-cdk-lib';
import {
  IAuthorizer,
  JsonSchemaType,
  JsonSchemaVersion,
  LambdaIntegration,
  Model,
  RequestValidator,
  Resource,
} from 'aws-cdk-lib/aws-apigateway';
import { MethodOptions } from 'aws-cdk-lib/aws-apigateway/lib/method';
import { Table } from 'aws-cdk-lib/aws-dynamodb';
import { Effect, PolicyStatement, Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';
import { Architecture, LayerVersion, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';

export interface DeleteEndpointsApiProps {
  router: Resource;
  httpMethod: string;
  endpointDeploymentTable: Table;
  multiUserTable: Table;
  srcRoot: string;
  commonLayer: LayerVersion;
  authorizer: IAuthorizer;
  logLevel: CfnParameter;
}

export class DeleteEndpointsApi {
  private readonly src: string;
  private readonly router: Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly endpointDeploymentTable: Table;
  private readonly multiUserTable: Table;
  private readonly layer: LayerVersion;
  private readonly baseId: string;
  private readonly authorizer: IAuthorizer;
  private readonly logLevel: CfnParameter;

  constructor(scope: Construct, id: string, props: DeleteEndpointsApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.endpointDeploymentTable = props.endpointDeploymentTable;
    this.multiUserTable = props.multiUserTable;
    this.authorizer = props.authorizer;
    this.src = props.srcRoot;
    this.layer = props.commonLayer;
    this.logLevel = props.logLevel;

    this.deleteEndpointsApi();
  }

  private iamRole(): Role {

    const newRole = new Role(this.scope, `${this.baseId}-role`, {
      assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
    });

    newRole.addToPolicy(new PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'sagemaker:DeleteModel',
        'sagemaker:DeleteEndpoint',
        'sagemaker:DescribeEndpoint',
        'sagemaker:DeleteEndpointConfig',
        'sagemaker:DescribeEndpointConfig',
      ],
      resources: [
        `arn:${Aws.PARTITION}:sagemaker:${Aws.REGION}:${Aws.ACCOUNT_ID}:model/*`,
        `arn:${Aws.PARTITION}:sagemaker:${Aws.REGION}:${Aws.ACCOUNT_ID}:endpoint/*`,
        `arn:${Aws.PARTITION}:sagemaker:${Aws.REGION}:${Aws.ACCOUNT_ID}:endpoint-config/*`,
      ],
    }));

    newRole.addToPolicy(new PolicyStatement({
      actions: [
        'dynamodb:Query',
        'dynamodb:GetItem',
        'dynamodb:PutItem',
        'dynamodb:DeleteItem',
        'dynamodb:UpdateItem',
        'dynamodb:Describe*',
        'dynamodb:List*',
        'dynamodb:Scan',
      ],
      resources: [
        this.endpointDeploymentTable.tableArn,
        this.multiUserTable.tableArn,
      ],
    }));

    newRole.addToPolicy(new PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'application-autoscaling:DeregisterScalableTarget',
      ],
      resources: [
        '*',
      ],
    }));

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

  private deleteEndpointsApi() {
    const lambdaFunction = new PythonFunction(this.scope, `${this.baseId}-lambda`, <PythonFunctionProps>{
      entry: `${this.src}/endpoints`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_9,
      index: 'delete_endpoints.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.iamRole(),
      memorySize: 1024,
      environment: {
        DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME: this.endpointDeploymentTable.tableName,
        MULTI_USER_TABLE: this.multiUserTable.tableName,
        LOG_LEVEL: this.logLevel.valueAsString,
      },
      layers: [this.layer],
    });

    const model = new Model(this.scope, `${this.baseId}-model`, {
      restApi: this.router.api,
      modelName: this.baseId,
      description: `${this.baseId} Request Model`,
      schema: {
        schema: JsonSchemaVersion.DRAFT4,
        title: this.baseId,
        type: JsonSchemaType.OBJECT,
        properties: {
          endpoint_name_list: {
            type: JsonSchemaType.ARRAY,
            items: {
              type: JsonSchemaType.STRING,
              minLength: 1,
            },
            minItems: 1,
            maxItems: 10,
          },
          username: {
            type: JsonSchemaType.STRING,
          },
        },
        required: [
          'endpoint_name_list',
          'username',
        ],
      },
      contentType: 'application/json',
    });

    const deleteEndpointsIntegration = new LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    const requestValidator = new RequestValidator(this.scope, `${this.baseId}-validator`, {
      restApi: this.router.api,
      requestValidatorName: this.baseId,
      validateRequestBody: true,
    });

    this.router.addMethod(this.httpMethod, deleteEndpointsIntegration, <MethodOptions>{
      apiKeyRequired: true,
      authorizer: this.authorizer,
      requestValidator,
      requestModels: {
        'application/json': model,
      },
    });

  }
}
