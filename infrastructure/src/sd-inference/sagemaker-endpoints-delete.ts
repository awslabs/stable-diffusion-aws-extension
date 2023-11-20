import { PythonFunction, PythonFunctionProps } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, Duration } from 'aws-cdk-lib';
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

export interface DeleteSagemakerEndpointsApiProps {
  router: Resource;
  httpMethod: string;
  endpointDeploymentTable: Table;
  multiUserTable: Table;
  srcRoot: string;
  commonLayer: LayerVersion;
  authorizer: IAuthorizer;
}

export class DeleteSagemakerEndpointsApi {
  private readonly src;
  private readonly router: Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly endpointDeploymentTable: Table;
  private readonly multiUserTable: Table;
  private readonly layer: LayerVersion;
  private readonly baseId: string;
  private readonly authorizer: IAuthorizer;

  constructor(scope: Construct, id: string, props: DeleteSagemakerEndpointsApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.endpointDeploymentTable = props.endpointDeploymentTable;
    this.multiUserTable = props.multiUserTable;
    this.authorizer = props.authorizer;
    this.src = props.srcRoot;
    this.layer = props.commonLayer;

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
        'sagemaker:DeleteEndpointConfig',
      ],
      resources: [
        `arn:${Aws.PARTITION}:sagemaker:${Aws.REGION}:${Aws.ACCOUNT_ID}:model/infer-model-*`,
        `arn:${Aws.PARTITION}:sagemaker:${Aws.REGION}:${Aws.ACCOUNT_ID}:endpoint/infer-endpoint-*`,
        `arn:${Aws.PARTITION}:sagemaker:${Aws.REGION}:${Aws.ACCOUNT_ID}:endpoint-config/infer-config-*`,
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
    const lambdaFunction = new PythonFunction(this.scope, `${this.baseId}-delete-endpoints`, <PythonFunctionProps>{
      functionName: `${this.baseId}-function`,
      entry: `${this.src}/inference_v2`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_9,
      index: 'sagemaker_endpoint_api.py',
      handler: 'delete_sagemaker_endpoints',
      timeout: Duration.seconds(900),
      role: this.iamRole(),
      memorySize: 1024,
      environment: {
        DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME: this.endpointDeploymentTable.tableName,
        MULTI_USER_TABLE: this.multiUserTable.tableName,
      },
      layers: [this.layer],
    });

    const model = new Model(this.scope, 'DeleteEndpointsModel', {
      restApi: this.router.api,
      modelName: 'DeleteEndpointsModel',
      description: 'Delete Endpoint Model',
      schema: {
        schema: JsonSchemaVersion.DRAFT4,
        title: 'deleteEndpointSchema',
        type: JsonSchemaType.OBJECT,
        properties: {
          delete_endpoint_list: {
            type: JsonSchemaType.ARRAY,
            items: {
              type: JsonSchemaType.STRING,
            },
            minItems: 1,
            maxItems: 10,
          },
          username: {
            type: JsonSchemaType.STRING,
          },
        },
        required: [
          'delete_endpoint_list',
          'username',
        ],
      },
      contentType: 'application/json',
    });

    const deleteEndpointsIntegration = new LambdaIntegration(
      lambdaFunction,
      {
        proxy: false,
        integrationResponses: [{ statusCode: '200' }],
      },
    );

    const requestValidator = new RequestValidator(this.scope, 'DeleteEndpointRequestValidator', {
      restApi: this.router.api,
      requestValidatorName: 'DeleteEndpointRequestValidator',
      validateRequestBody: true,
    });

    this.router.addMethod(this.httpMethod, deleteEndpointsIntegration, <MethodOptions>{
      apiKeyRequired: true,
      authorizer: this.authorizer,
      requestValidator,
      requestModels: {
        'application/json': model,
      },
      methodResponses: [
        {
          statusCode: '200',
        }, { statusCode: '500' },
      ],
    });

  }
}
