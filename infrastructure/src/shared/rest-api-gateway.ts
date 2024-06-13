import {
  AccessLogFormat,
  CfnRestApi,
  Cors,
  EndpointType,
  LogGroupLogDestination,
  ResponseType,
  RestApi
} from 'aws-cdk-lib/aws-apigateway';
import { Resource } from 'aws-cdk-lib/aws-apigateway/lib/resource';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';
import { ApiModels } from './models';
import {SCHEMA_202, SCHEMA_204, SCHEMA_400, SCHEMA_401, SCHEMA_403, SCHEMA_404, SCHEMA_504} from './schema';
import { ESD_VERSION } from './version';
import { ApiValidators } from './validator';
import {AnyPrincipal, PolicyDocument, PolicyStatement} from "aws-cdk-lib/aws-iam";
import {CfnParameter} from "aws-cdk-lib";

export class RestApiGateway {
  public apiGateway: RestApi;
  public readonly apiKey: string;
  public readonly routers: { [key: string]: Resource } = {};
  private readonly scope: Construct;
  private readonly apiEndpointType: CfnParameter;

  constructor(scope: Construct, apiKey: string, apiEndpointType:CfnParameter, routes: string[]) {
    this.apiEndpointType = apiEndpointType;
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

  private createApigw(apiKeyStr: string): [RestApi, string] {
    const apiAccessLogGroup = new logs.LogGroup(
      this.scope,
      'aigc-api-logs',
    );

    // const isPrivateApiCondition = new CfnCondition(this.scope, 'IsPrivateApi', {
    //   expression: Fn.conditionEquals(this.apiEndpointType.valueAsString, 'PRIVATE')
    // });

    // Create an API Gateway, will merge with existing API Gateway
    const api = new RestApi(this.scope, 'sd-extension-deploy-api', {
      restApiName: this.scope.node.id,
      description: `Extension for Stable Diffusion on AWS API - ${ESD_VERSION}`,
      deployOptions: {
        accessLogDestination: new LogGroupLogDestination(apiAccessLogGroup),
        accessLogFormat: AccessLogFormat.clf(),
      },
      endpointConfiguration: {
        types: [
          this.apiEndpointType.valueAsString as EndpointType
        ],
      },
      defaultCorsPreflightOptions: {
        allowOrigins: Cors.ALL_ORIGINS,
        allowMethods: Cors.ALL_METHODS,
        allowHeaders: ['*'],
      },
    });

    (api.node.defaultChild as CfnRestApi).policy = new PolicyDocument({
      statements: [
        new PolicyStatement({
          actions: ['execute-api:Invoke'],
          resources: [`*`],
          principals: [new AnyPrincipal()],
        }),
      ],
    });

    this.createResponses(api);

    ApiModels.schema202 = ApiModels.createAPiModel(this.scope, api, SCHEMA_202, '202');
    ApiModels.schema204 = ApiModels.createAPiModel(this.scope, api, SCHEMA_204, '204');
    ApiModels.schema400 = ApiModels.createAPiModel(this.scope, api, SCHEMA_400, '400');
    ApiModels.schema401 = ApiModels.createAPiModel(this.scope, api, SCHEMA_401, '401');
    ApiModels.schema403 = ApiModels.createAPiModel(this.scope, api, SCHEMA_403, '403');
    ApiModels.schema404 = ApiModels.createAPiModel(this.scope, api, SCHEMA_404, '404');
    ApiModels.schema504 = ApiModels.createAPiModel(this.scope, api, SCHEMA_504, '504');

    ApiValidators.createBodyValidator(this.scope, api, 'esd-api');

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
    usagePlan.node.addDependency(apiKey);

    return [api, apiKeyStr];
  }

  private createResponses(api: RestApi) {

    api.addGatewayResponse('BAD_REQUEST_BODY', {
      type: ResponseType.BAD_REQUEST_BODY,
      templates: {
        'application/json': JSON.stringify({
          statusCode: 400,
          message: '$context.error.validationErrorString',
          requestId: '$context.extendedRequestId',
        }),
      },
    });

    api.addGatewayResponse('BAD_REQUEST_PARAMETERS', {
      type: ResponseType.BAD_REQUEST_PARAMETERS,
      templates: {
        'application/json': JSON.stringify({
          statusCode: 400,
          message: '$context.error.validationErrorString',
          requestId: '$context.extendedRequestId',
        }),
      },
    });

    api.addGatewayResponse('DEFAULT_4XX', {
      type: ResponseType.DEFAULT_4XX,
      templates: {
        'application/json': JSON.stringify({
          message: '$context.error.message',
          requestId: '$context.extendedRequestId',
        }),
      },
    });

    api.addGatewayResponse('DEFAULT_5XX', {
      type: ResponseType.DEFAULT_5XX,
      templates: {
        'application/json': JSON.stringify({
          message: '$context.error.message',
          requestId: '$context.extendedRequestId',
        }),
      },
    });
  }
}
