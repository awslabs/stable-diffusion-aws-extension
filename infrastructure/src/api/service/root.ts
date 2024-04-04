import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, aws_lambda, Duration } from 'aws-cdk-lib';
import { LambdaIntegration, RestApi } from 'aws-cdk-lib/aws-apigateway';
import { Effect, PolicyStatement, Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';
import { Architecture, LayerVersion, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';

export interface RootAPIProps {
  httpMethod: string;
  commonLayer: LayerVersion;
  restApi: RestApi;
}

export class RootAPI {
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly layer: LayerVersion;
  private readonly restApi: RestApi;
  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: RootAPIProps) {
    this.scope = scope;
    this.baseId = id;
    this.restApi = props.restApi;
    this.httpMethod = props.httpMethod;
    this.layer = props.commonLayer;

    const lambdaFunction = this.apiLambda();

    const lambdaIntegration = new LambdaIntegration(lambdaFunction, { proxy: true });

    this.restApi.root.addMethod(this.httpMethod, lambdaIntegration, {
      apiKeyRequired: true,
      operationName: 'RootAPI',
      requestValidatorOptions: {
        requestValidatorName: `${this.baseId}-validator`,
        validateRequestBody: true,
        validateRequestParameters: true,
      },
      requestParameters: {
        'method.request.header.MyHeader': false,
        'method.request.header.MyHeader2': true,
        'method.request.querystring.myQuery': true,
        'method.request.querystring.myQuery2': false,
      },
      methodResponses: [
        ApiModels.methodResponses403(),
      ],
    });
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

  private apiLambda() {
    return new PythonFunction(this.scope,
      `${this.baseId}-lambda`,
      {
        entry: '../middleware_api/service',
        architecture: Architecture.X86_64,
        runtime: Runtime.PYTHON_3_10,
        index: 'root.py',
        handler: 'handler',
        timeout: Duration.seconds(900),
        role: this.iamRole(),
        memorySize: 2048,
        tracing: aws_lambda.Tracing.ACTIVE,
        layers: [this.layer],
      });
  }
}
