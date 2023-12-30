import { PythonFunction, PythonFunctionProps } from '@aws-cdk/aws-lambda-python-alpha';
import { aws_apigateway, aws_dynamodb, aws_iam, aws_kms, aws_lambda, Duration } from 'aws-cdk-lib';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { ResourceProvider } from './resource-provider';

export interface UserUpsertApiProps {
  multiUserTable: aws_dynamodb.Table;
  commonLayer: aws_lambda.LayerVersion;
  resourceProvider: ResourceProvider;
}

export class AuthorizerLambda {
  public readonly authorizer: aws_apigateway.IAuthorizer;
  public readonly passwordKeyAlias: aws_kms.IKey;
  private readonly srcRoot = '../middleware_api/lambda';
  private readonly scope: Construct;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly multiUserTable: aws_dynamodb.Table;

  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: UserUpsertApiProps) {
    this.scope = scope;
    this.baseId = id;

    const keyAlias = 'sd-extension-password-key';

    this.passwordKeyAlias = aws_kms.Alias.fromAliasName(scope, `${id}-createOrNew-passwordKey`, keyAlias);
    this.passwordKeyAlias.node.addDependency(props.resourceProvider.resources);
    this.layer = props.commonLayer;
    this.multiUserTable = props.multiUserTable;

    this.authorizer = this.createAuthorizer();
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
          'kms:RequestAlias': `alias/${this.passwordKeyAlias.keyId}`,
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

  private createAuthorizer(): aws_apigateway.IAuthorizer {
    const authFunction = new PythonFunction(this.scope, `${this.baseId}-lambda`, <PythonFunctionProps>{
      entry: `${this.srcRoot}/users`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_9,
      index: 'authorizer.py',
      handler: 'auth',
      timeout: Duration.seconds(900),
      role: this.iamRole(),
      memorySize: 1024,
      environment: {
        MULTI_USER_TABLE: this.multiUserTable.tableName,
        KEY_ID: `alias/${this.passwordKeyAlias.keyId}`,
      },
      layers: [this.layer],
    });
    return new aws_apigateway.TokenAuthorizer(this.scope, `${this.baseId}-NewRequestAuthorizer`, {
      handler: authFunction,
      resultsCacheTtl: Duration.millis(0),
      identitySource: 'method.request.header.Authorization',
    });
  }

}

