import { aws_lambda, CfnParameter, CustomResource, Duration } from 'aws-cdk-lib';
import { Runtime } from 'aws-cdk-lib/aws-lambda';
import { NodejsFunction } from 'aws-cdk-lib/aws-lambda-nodejs';
import { RetentionDays } from 'aws-cdk-lib/aws-logs';
import { Provider } from 'aws-cdk-lib/custom-resources';
import { Construct } from 'constructs';
import { ResourceProvider } from './resource-provider';
import { RestApiGateway } from './rest-api-gateway';

export interface ResourceWaiterProps {
  resourceProvider: ResourceProvider;
  restApiGateway: RestApiGateway;
  apiKeyParam: CfnParameter;
  timestamp?: string;
}

export class ResourceWaiter extends Construct {

  constructor(scope: Construct, id: string, props: ResourceWaiterProps) {
    super(scope, id);

    const role = props.resourceProvider.role;

    const handler = new NodejsFunction(scope, 'ResourcesWaiterHandler', {
      runtime: Runtime.NODEJS_18_X,
      handler: 'handler',
      entry: 'src/shared/resource-waiter-on-event.ts',
      bundling: {
        minify: true,
        externalModules: ['aws-cdk-lib'],
      },
      timeout: Duration.seconds(900),
      role: role,
      memorySize: 3070,
      tracing: aws_lambda.Tracing.ACTIVE,
    });

    const provider = new Provider(scope, 'ResourcesWaiterProvider', {
      onEventHandler: handler,
      logRetention: RetentionDays.ONE_DAY,
    });

    const waiter1 = new CustomResource(scope, 'ResourcesWaiterCustomResource1', {
      serviceToken: provider.serviceToken,
      properties: {
        apiUrl: props.restApiGateway.apiGateway.url,
        apiKey: props.apiKeyParam.valueAsString,
        timestamp: props.timestamp,
        name: 'Waiter1',
      },
    });

    const waiter2 = new CustomResource(scope, 'ResourcesWaiterCustomResource2', {
      serviceToken: provider.serviceToken,
      properties: {
        apiUrl: props.restApiGateway.apiGateway.url,
        apiKey: props.apiKeyParam.valueAsString,
        timestamp: props.timestamp,
        name: 'Waiter2',
      },
    });
    waiter2.node.addDependency(waiter1);

    const waiter3 = new CustomResource(scope, 'ResourcesWaiterCustomResource3', {
      serviceToken: provider.serviceToken,
      properties: {
        apiUrl: props.restApiGateway.apiGateway.url,
        apiKey: props.apiKeyParam.valueAsString,
        timestamp: props.timestamp,
        name: 'Waiter3',
      },
    });
    waiter3.node.addDependency(waiter2);

  }

}
