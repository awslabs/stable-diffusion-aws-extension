import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import {Aws, aws_apigateway, aws_dynamodb, aws_lambda, Duration} from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model } from 'aws-cdk-lib/aws-apigateway';
import {Role} from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { ApiModels } from '../../shared/models';
import { SCHEMA_USERNAME } from '../../shared/schema';
import { ApiValidators } from '../../shared/validator';
import {ESD_ROLE} from "../../shared/const";

export interface DeleteUsersApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  multiUserTable: aws_dynamodb.Table;
  commonLayer: aws_lambda.LayerVersion;
}

export class DeleteUsersApi {
  private readonly router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: DeleteUsersApiProps) {
    this.scope = scope;
    this.httpMethod = props.httpMethod;
    this.baseId = id;
    this.router = props.router;
    this.layer = props.commonLayer;

    const lambdaFunction = this.apiLambda();

    const lambdaIntegration = new LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.addMethod(this.httpMethod, lambdaIntegration, {
      apiKeyRequired: true,
      requestValidator: ApiValidators.bodyValidator,
      requestModels: {
        'application/json': this.createRequestBodyModel(),
      },
      operationName: 'DeleteUsers',
      methodResponses: [
        ApiModels.methodResponses204(),
        ApiModels.methodResponses400(),
        ApiModels.methodResponses401(),
        ApiModels.methodResponses403(),
        ApiModels.methodResponses404(),
      ],
    });
  }

  private createRequestBodyModel(): Model {
    return new Model(this.scope, `${this.baseId}-model`, {
      restApi: this.router.api,
      modelName: `${this.baseId}Request`,
      description: `Request Model ${this.baseId}`,
      schema: {
        schema: JsonSchemaVersion.DRAFT7,
        title: this.baseId,
        type: JsonSchemaType.OBJECT,
        properties: {
          user_name_list: {
            type: JsonSchemaType.ARRAY,
            items: SCHEMA_USERNAME,
            minItems: 1,
            maxItems: 100,
          },
        },
        required: [
          'user_name_list',
        ],
      },
      contentType: 'application/json',
    });
  }

  private apiLambda() {
    const role = <Role>Role.fromRoleName(this.scope, `${this.baseId}-role`, `${ESD_ROLE}-${Aws.REGION}`);

    return new PythonFunction(this.scope, `${this.baseId}-lambda`, {
      entry: '../middleware_api/users',
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'delete_users.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: role,
      memorySize: 2048,
      tracing: aws_lambda.Tracing.ACTIVE,
      layers: [this.layer],
    });
  }

}

