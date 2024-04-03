import { JsonSchema, Model, RestApi } from 'aws-cdk-lib/aws-apigateway';
import { MethodResponse } from 'aws-cdk-lib/aws-apigateway/lib/methodresponse';
import { Construct } from 'constructs';


export class ApiModels {

  public static schema400: Model;
  public static schema401: Model;
  public static schema403: Model;
  public static schema404: Model;
  public static schema504: Model;

  public static methodResponses(model200: Model): MethodResponse[] {
    return [
      {
        statusCode: '200',
        responseModels: {
          'application/json': model200,
        },
        responseParameters: {
          'method.response.header.Access-Control-Allow-Origin': true,
        },
      },
      {
        statusCode: '400',
        responseModels: {
          'application/json': this.schema400,
        },
        responseParameters: {
          'method.response.header.Access-Control-Allow-Origin': true,
        },
      },
      {
        statusCode: '401',
        responseModels: {
          'application/json': this.schema401,
        },
        responseParameters: {
          'method.response.header.Access-Control-Allow-Origin': true,
        },
      },
      {
        statusCode: '403',
        responseModels: {
          'application/json': this.schema403,
        },
        responseParameters: {
          'method.response.header.Access-Control-Allow-Origin': true,
        },
      },
      {
        statusCode: '404',
        responseModels: {
          'application/json': this.schema404,
        },
        responseParameters: {
          'method.response.header.Access-Control-Allow-Origin': true,
        },
      },
      {
        statusCode: '504',
        responseModels: {
          'application/json': this.schema504,
        },
        responseParameters: {
          'method.response.header.Access-Control-Allow-Origin': true,
        },
      },
    ];
  }

  public static createAPiModel(scope: Construct, restApi: RestApi, schema: JsonSchema, modelName: string) {
    return new Model(scope, `model-${modelName}`, {
      restApi: restApi,
      modelName: modelName,
      description: `${modelName} Model`,
      schema: schema,
      contentType: 'application/json',
    });
  }


}
