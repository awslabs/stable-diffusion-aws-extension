import { RequestValidator, RestApi } from 'aws-cdk-lib/aws-apigateway';
import { Construct } from 'constructs';


export class ApiValidators {

  public static validator: RequestValidator;

  public static createValidator(scope: Construct, restApi: RestApi, name: string) {
    ApiValidators.validator =new RequestValidator(
      scope,
      `${name}-validator`,
      {
        restApi: restApi,
        validateRequestBody: true,
      });
  }


}
