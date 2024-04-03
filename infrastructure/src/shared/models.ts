import { JsonSchema, Model, RestApi } from 'aws-cdk-lib/aws-apigateway';
import { Construct } from 'constructs';
import { SCHEMA_400, SCHEMA_401, SCHEMA_403, SCHEMA_404, SCHEMA_504 } from './schema';


export class ApiModels {

  public static get_400(scope: Construct, restApi: RestApi): Model {
    if (!this.schema400) {
      this.schema400 = this.createAPiModel(scope, restApi, SCHEMA_400, '400');
    }

    return this.schema400;
  }

  public static get_401(scope: Construct, restApi: RestApi): Model {
    if (!this.schema401) {
      this.schema401 = this.createAPiModel(scope, restApi, SCHEMA_401, '401');
    }

    return this.schema401;
  }


  public static get_403(scope: Construct, restApi: RestApi): Model {
    if (!this.schema403) {
      this.schema403 = this.createAPiModel(scope, restApi, SCHEMA_403, '403');
    }

    return this.schema403;
  }


  public static get_404(scope: Construct, restApi: RestApi): Model {
    if (!this.schema404) {
      this.schema404 = this.createAPiModel(scope, restApi, SCHEMA_404, '404');
    }

    return this.schema404;
  }

  public static get_504(scope: Construct, restApi: RestApi): Model {
    if (!this.schema504) {
      this.schema504 = this.createAPiModel(scope, restApi, SCHEMA_504, '504');
    }

    return this.schema504;
  }

  private static schema400: Model;
  private static schema401: Model;
  private static schema403: Model;
  private static schema404: Model;
  private static schema504: Model;

  private static createAPiModel(scope: Construct, restApi: RestApi, schema: JsonSchema, modelName: string) {
    return new Model(scope, `model-${modelName}`, {
      restApi: restApi,
      modelName: modelName,
      description: `${modelName} Model`,
      schema: schema,
      contentType: 'application/json',
    });
  }


}
