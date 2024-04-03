import { aws_apigateway as apigw } from 'aws-cdk-lib';
import { AccessLogFormat, LogGroupLogDestination } from 'aws-cdk-lib/aws-apigateway';
import { Resource } from 'aws-cdk-lib/aws-apigateway/lib/resource';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';
import { ApiModels } from './models';
import { SCHEMA_400, SCHEMA_401, SCHEMA_403, SCHEMA_404, SCHEMA_504 } from './schema';
import { ESD_VERSION } from './version';

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
      restApiName: this.scope.node.id,
      description: `Extension for Stable Diffusion on AWS API - ${ESD_VERSION}`,
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
    });

    ApiModels.schema400 = ApiModels.createAPiModel(this.scope, api, SCHEMA_400, '400');
    ApiModels.schema401 = ApiModels.createAPiModel(this.scope, api, SCHEMA_401, '401');
    ApiModels.schema403 = ApiModels.createAPiModel(this.scope, api, SCHEMA_403, '403');
    ApiModels.schema404 = ApiModels.createAPiModel(this.scope, api, SCHEMA_404, '404');
    ApiModels.schema504 = ApiModels.createAPiModel(this.scope, api, SCHEMA_504, '504');

    // custom error response to return details of validation errors to the client.
    const responseBad = api.addGatewayResponse('BAD_REQUEST_BODY', {
      type: apigw.ResponseType.BAD_REQUEST_BODY,
      templates: {
        'application/json': JSON.stringify({
          statusCode: 400,
          message: '$context.error.validationErrorString',
          requestId: '$context.requestId',
        }),
      },
    });

    const response400 = api.addGatewayResponse('DEFAULT_4XX', {
      type: apigw.ResponseType.DEFAULT_4XX,
      templates: {
        'application/json': JSON.stringify({
          message: '$context.error.message',
          requestId: '$context.requestId',
        }),
      },
    });
    response400.node.addDependency(responseBad);

    const response500 = api.addGatewayResponse('DEFAULT_5XX', {
      type: apigw.ResponseType.DEFAULT_5XX,
      templates: {
        'application/json': JSON.stringify({
          message: '$context.error.message',
          requestId: '$context.requestId',
        }),
      },
    });
    response500.node.addDependency(response400);

    // Add API Key to the API Gateway
    const apiKey = api.addApiKey('sd-extension-api-key', {
      apiKeyName: 'sd-extension-api-key',
      value: apiKeyStr,
    });
    apiKey.node.addDependency(response500);

    const usagePlan = api.addUsagePlan('sd-extension-api-usage-plan', {});
    usagePlan.addApiKey(apiKey);
    usagePlan.addApiStage({
      stage: api.deploymentStage,
    });
    usagePlan.node.addDependency(apiKey);

    return [api, apiKeyStr];
  }
}
