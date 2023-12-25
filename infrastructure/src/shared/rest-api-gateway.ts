import { aws_apigateway as apigw, CfnOutput } from 'aws-cdk-lib';
import { AccessLogFormat, LogGroupLogDestination } from 'aws-cdk-lib/aws-apigateway';
import { Resource } from 'aws-cdk-lib/aws-apigateway/lib/resource';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';

export class RestApiGateway {
  public apiGateway: apigw.RestApi;
  public readonly apiKey: string;
  public readonly routers: { [key: string]: Resource } = {};
  private readonly scope: Construct;

  constructor(scope: Construct, apiKey: string, routes: string[]) {
    this.scope = scope;
    [this.apiGateway, this.apiKey] = this.createApigw(apiKey);
    for (let route of routes) {
      const pathList: string[] = route.split('/');
      // pathList has at least one item
      let pathResource: Resource = this.apiGateway.root.addResource(pathList[0]);
      for (let i = 1; i < pathList.length; i++) {
        let pathPart: string = pathList[i];
        pathResource = pathResource.addResource(pathPart);
      }
      this.routers[route] = pathResource;
    }
  }

  private createApigw(apiKeyStr: string): [apigw.RestApi, string] {
    const apiAccessLogGroup = new logs.LogGroup(
      this.scope,
      'aigc-api-logs',
    );

    // Create an API Gateway, will merge with existing API Gateway
    const api = new apigw.RestApi(this.scope, 'sd-extension-deploy-api', {
      restApiName: 'Stable Diffusion Train and Deploy API',
      description:
                'This service is used to train and deploy Stable Diffusion models.',
      deployOptions: {
        accessLogDestination: new LogGroupLogDestination(apiAccessLogGroup),
        accessLogFormat: AccessLogFormat.clf(),
      },
      endpointConfiguration: {
        types: [apigw.EndpointType.EDGE],
      },
      defaultCorsPreflightOptions: {
        allowOrigins: apigw.Cors.ALL_ORIGINS, // You can also provide a list of specific origins ['https://example.com']
        allowMethods: apigw.Cors.ALL_METHODS, // You can also provide a list of specific methods ['GET', 'POST', 'OPTIONS']
        allowHeaders: ['Content-Type', 'X-Amz-Date', 'Authorization', 'X-Api-Key', 'X-Amz-Security-Token', 'X-Amz-User-Agent'], // Customize as needed
      },
      endpointConfiguration: {
        types: [apigw.EndpointType.REGIONAL],
      },
    });

    // custom error response to return details of validation errors to the client.
    api.addGatewayResponse('BAD_REQUEST_BODY', {
      type: apigw.ResponseType.BAD_REQUEST_BODY,
      templates: {
        'application/json': JSON.stringify({
          statusCode: 400,
          message: '$context.error.validationErrorString',
        }),
      },
    });

    api.addGatewayResponse('DEFAULT_4XX', {
      type: apigw.ResponseType.DEFAULT_4XX,
      templates: {
        'application/json': JSON.stringify({
          message: '$context.error.message',
        }),
      },
    });

    api.addGatewayResponse('DEFAULT_5XX', {
      type: apigw.ResponseType.DEFAULT_5XX,
      templates: {
        'application/json': JSON.stringify({
          message: '$context.error.message',
        }),
      },
    });

    // Add API Key to the API Gateway
    const apiKey = api.addApiKey('sd-extension-api-key', {
      apiKeyName: 'sd-extension-api-key',
      value: apiKeyStr,
    });

    const usagePlan = api.addUsagePlan('sd-extension-api-usage-plan', {});
    usagePlan.addApiKey(apiKey);
    usagePlan.addApiStage({
      stage: api.deploymentStage,
    });
    // Output the API Gateway URL
    new CfnOutput(this.scope, 'train-deploy-api-url', {
      value: api.url,
    });

    return [api, apiKeyStr];
  }
}
