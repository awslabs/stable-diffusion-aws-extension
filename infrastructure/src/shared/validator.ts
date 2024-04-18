import { RequestValidator, RestApi } from 'aws-cdk-lib/aws-apigateway';
import { Construct } from 'constructs';


export class ApiValidators {

  public static bodyValidator: RequestValidator;

  public static createBodyValidator(scope: Construct, restApi: RestApi, name: string) {
    ApiValidators.bodyValidator =new RequestValidator(
      scope,
      `${name}-validator`,
      {
        restApi: restApi,
        validateRequestBody: true,
      });
  }

}
