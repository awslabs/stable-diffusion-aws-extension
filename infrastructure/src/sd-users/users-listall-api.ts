import { PythonFunction, PythonFunctionProps } from '@aws-cdk/aws-lambda-python-alpha';
import {
  aws_apigateway,
  aws_apigateway as apigw,
  aws_dynamodb,
  aws_iam, aws_kms,
  aws_lambda,
  Duration,
} from 'aws-cdk-lib';
import { MethodOptions } from 'aws-cdk-lib/aws-apigateway/lib/method';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';


export interface ListAllUsersApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  multiUserTable: aws_dynamodb.Table;
  srcRoot: string;
  commonLayer: aws_lambda.LayerVersion;
  passwordKey: aws_kms.IKey;
  authorizer: aws_apigateway.IAuthorizer;
}

export class ListAllUsersApi {
  private readonly src;
  private readonly router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly multiUserTable: aws_dynamodb.Table;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly passwordKey: aws_kms.IKey;
  private readonly baseId: string;
  private readonly authorizer: aws_apigateway.IAuthorizer;

  constructor(scope: Construct, id: string, props: ListAllUsersApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.passwordKey = props.passwordKey;
    this.httpMethod = props.httpMethod;
    this.multiUserTable = props.multiUserTable;
    this.src = props.srcRoot;
    this.layer = props.commonLayer;
    this.authorizer = props.authorizer;

    this.listAllUsersApi();
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

  private listAllUsersApi() {
    const lambdaFunction = new PythonFunction(this.scope, `${this.baseId}-lambda`, <PythonFunctionProps>{
      entry: `${this.src}/multi_users`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_9,
      index: 'multi_users_api.py',
      handler: 'list_user',
      timeout: Duration.seconds(900),
      role: this.iamRole(),
      memorySize: 1024,
      environment: {
        MULTI_USER_TABLE: this.multiUserTable.tableName,
        KEY_ID: `alias/${this.passwordKey.keyId}`,
      },
      layers: [this.layer],
    });

    const listUsersIntegration = new apigw.LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );
    this.router.addMethod(this.httpMethod, listUsersIntegration, <MethodOptions>{
      apiKeyRequired: true,
      authorizer: this.authorizer,
    });
  }
}

