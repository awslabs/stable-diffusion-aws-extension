import { CfnParameter, CustomResource, Duration } from 'aws-cdk-lib';
import { Role } from 'aws-cdk-lib/aws-iam';
import { Runtime } from 'aws-cdk-lib/aws-lambda';
import { NodejsFunction } from 'aws-cdk-lib/aws-lambda-nodejs';
import { RetentionDays } from 'aws-cdk-lib/aws-logs';
import { Size } from 'aws-cdk-lib/core';
import { Provider } from 'aws-cdk-lib/custom-resources';
import { Construct } from 'constructs';
import { ResourceProvider } from './resource-provider';
import { RestApiGateway } from './rest-api-gateway';

export interface ResourceCheckerProps {
  resourceProvider: ResourceProvider;
  restApiGateway: RestApiGateway;
  apiKeyParam: CfnParameter;
}

export class ResourceChecker extends Construct {

  public readonly resources: CustomResource;
  public readonly role: Role;
  public readonly handler: NodejsFunction;
  public readonly provider: Provider;

  constructor(scope: Construct, id: string, props: ResourceCheckerProps) {
    super(scope, id);

    this.role = props.resourceProvider.role;

    this.handler = new NodejsFunction(scope, 'ResourceCheckerHandler', {
      runtime: Runtime.NODEJS_18_X,
      handler: 'handler',
      entry: 'src/shared/resource-checker-on-event.ts',
      bundling: {
        minify: true,
        externalModules: ['aws-cdk-lib'],
      },
      timeout: Duration.seconds(900),
      role: this.role,
      memorySize: 10240,
      ephemeralStorageSize: Size.gibibytes(10),
      environment: {
        ROLE_ARN: this.role.roleArn,
      },
    });

    this.provider = new Provider(scope, 'ResourceChecker', {
      onEventHandler: this.handler,
      logRetention: RetentionDays.ONE_DAY,
    });

    this.resources = new CustomResource(scope, 'ResourceChecker', {
      serviceToken: this.provider.serviceToken,
      properties: {
        apiKey: props.apiKeyParam.valueAsString,
        restApiId: props.restApiGateway.apiGateway.url,
      },
    });

  }

}
