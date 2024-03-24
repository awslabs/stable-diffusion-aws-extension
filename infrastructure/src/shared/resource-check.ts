import { CfnParameter, CustomResource, Duration } from 'aws-cdk-lib';
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

  constructor(scope: Construct, id: string, props: ResourceCheckerProps) {
    super(scope, id);

    const role = props.resourceProvider.role;

    const handler = new NodejsFunction(scope, 'ResourceCheckerHandler', {
      runtime: Runtime.NODEJS_18_X,
      handler: 'handler',
      entry: 'src/shared/resource-checker-on-event.ts',
      bundling: {
        minify: true,
        externalModules: ['aws-cdk-lib'],
      },
      timeout: Duration.seconds(900),
      role: role,
      memorySize: 10240,
      ephemeralStorageSize: Size.gibibytes(10),
    });

    const provider = new Provider(scope, 'ResourceChecker', {
      onEventHandler: handler,
      logRetention: RetentionDays.ONE_DAY,
    });

    new CustomResource(scope, 'ResourceChecker', {
      serviceToken: provider.serviceToken,
      properties: {
        apiKey: props.apiKeyParam.valueAsString,
        restApiId: props.restApiGateway.apiGateway.url,
      },
    });

  }

}
