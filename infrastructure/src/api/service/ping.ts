import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, Duration } from 'aws-cdk-lib';
import { LambdaIntegration, Resource } from 'aws-cdk-lib/aws-apigateway';
import { Effect, PolicyStatement, Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';
import { Architecture, LayerVersion, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';

export interface PingApiProps {
  router: Resource;
  httpMethod: string;
  srcRoot: string;
  commonLayer: LayerVersion;
}

export class PingApi {
  private readonly src: string;
  private readonly router: Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly layer: LayerVersion;
  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: PingApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.src = props.srcRoot;
    this.layer = props.commonLayer;

    this.pingApi();
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

  private pingApi() {

    const lambdaFunction = new PythonFunction(
      this.scope,
      `${this.baseId}-lambda`,
      {
        entry: `${this.src}/service`,
        architecture: Architecture.X86_64,
        runtime: Runtime.PYTHON_3_9,
        index: 'ping.py',
        handler: 'handler',
        timeout: Duration.seconds(900),
        role: this.iamRole(),
        memorySize: 1024,
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
      });

  }
}
