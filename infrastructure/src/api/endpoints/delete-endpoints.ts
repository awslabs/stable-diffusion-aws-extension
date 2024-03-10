import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, CfnParameter, Duration } from 'aws-cdk-lib';
import {
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
  logLevel: CfnParameter;
}

export class DeleteEndpointsApi {
  public model: Model;
  public requestValidator: RequestValidator;
  private readonly src: string;
  private readonly router: Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly endpointDeploymentTable: Table;
  private readonly multiUserTable: Table;
  private readonly layer: LayerVersion;
  private readonly baseId: string;
  private readonly logLevel: CfnParameter;

  constructor(scope: Construct, id: string, props: DeleteEndpointsApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.endpointDeploymentTable = props.endpointDeploymentTable;
    this.multiUserTable = props.multiUserTable;
    this.src = props.srcRoot;
    this.layer = props.commonLayer;
    this.logLevel = props.logLevel;
    this.model = this.createModel();
    this.requestValidator = this.createRequestValidator();

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
          endpoint_name_list: {
            type: JsonSchemaType.ARRAY,
            items: {
              type: JsonSchemaType.STRING,
              minLength: 1,
            },
            minItems: 1,
            maxItems: 10,
          },
        },
        required: [
          'endpoint_name_list',
        ],
      },
      contentType: 'application/json',
    });
  }

  private createRequestValidator(): RequestValidator {
    return new RequestValidator(this.scope, `${this.baseId}-del-ep-validator`, {
      restApi: this.router.api,
      validateRequestBody: true,
    });
  }

  private deleteEndpointsApi() {
    const lambdaFunction = new PythonFunction(this.scope, `${this.baseId}-lambda`, {
      entry: `${this.src}/endpoints`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_12,
      index: 'delete_endpoints.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.iamRole(),
      memorySize: 2048,
      environment: {
        DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME: this.endpointDeploymentTable.tableName,
        MULTI_USER_TABLE: this.multiUserTable.tableName,
        LOG_LEVEL: this.logLevel.valueAsString,
      },
      layers: [this.layer],
    });


    const deleteEndpointsIntegration = new LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.addMethod(this.httpMethod, deleteEndpointsIntegration, <MethodOptions>{
      apiKeyRequired: true,
      requestValidator: this.requestValidator,
      requestModels: {
        'application/json': this.model,
      },
    });

  }
}
