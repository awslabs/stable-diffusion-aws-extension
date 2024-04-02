import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, aws_lambda, Duration } from 'aws-cdk-lib';
import {
  JsonSchemaType,
  JsonSchemaVersion,
  LambdaIntegration,
  Model,
  RequestValidator,
  Resource,
} from 'aws-cdk-lib/aws-apigateway';
import { Table } from 'aws-cdk-lib/aws-dynamodb';
import { Effect, PolicyStatement, Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';
import { Architecture, LayerVersion, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';

export interface DeleteRolesApiProps {
  router: Resource;
  httpMethod: string;
  multiUserTable: Table;
  srcRoot: string;
  commonLayer: LayerVersion;
}

export class DeleteRolesApi {
  public model: Model;
  public requestValidator: RequestValidator;
  private readonly src: string;
  private readonly router: Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly multiUserTable: Table;
  private readonly layer: LayerVersion;
  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: DeleteRolesApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.multiUserTable = props.multiUserTable;
    this.src = props.srcRoot;
    this.layer = props.commonLayer;
    this.model = this.createModel();
    this.requestValidator = this.createRequestValidator();

    this.deleteRolesApi();
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
      actions: [
        // query all users with the role
        'dynamodb:Query',
        // remove role from user
        'dynamodb:UpdateItem',
        // delete role
        'dynamodb:DeleteItem',
        // scan users
        'dynamodb:Scan',
      ],
      resources: [
        this.multiUserTable.tableArn,
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
    return new Model(
      this.scope,
      `${this.baseId}-model`,
      {
        restApi: this.router.api,
        modelName: this.baseId,
        description: `${this.baseId} Request Model`,
        schema: {
          schema: JsonSchemaVersion.DRAFT7,
          title: this.baseId,
          type: JsonSchemaType.OBJECT,
          properties: {
            role_name_list: {
              type: JsonSchemaType.ARRAY,
              items: {
                type: JsonSchemaType.STRING,
                minLength: 1,
              },
              minItems: 1,
              maxItems: 100,
            },
          },
          required: [
            'role_name_list',
          ],
        },
        contentType: 'application/json',
      });
  }

  private createRequestValidator(): RequestValidator {
    return new RequestValidator(
      this.scope,
      `${this.baseId}-del-role-validator`,
      {
        restApi: this.router.api,
        validateRequestBody: true,
      });
  }

  private deleteRolesApi() {

    const lambdaFunction = new PythonFunction(
      this.scope,
      `${this.baseId}-lambda`,
      {
        entry: `${this.src}/roles`,
        architecture: Architecture.X86_64,
        runtime: Runtime.PYTHON_3_10,
        index: 'delete_roles.py',
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

    this.router.addMethod(
      this.httpMethod,
      lambdaIntegration,
      {
        apiKeyRequired: true,
        requestValidator: this.requestValidator,
        requestModels: {
          'application/json': this.model,
        },
      });

  }
}
