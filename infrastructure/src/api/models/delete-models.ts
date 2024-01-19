import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, CfnParameter, Duration } from 'aws-cdk-lib';
import {
  JsonSchemaType,
  JsonSchemaVersion,
  LambdaIntegration,
  Model,
  RequestValidator,
  Resource,
} from 'aws-cdk-lib/aws-apigateway';
import { Table } from 'aws-cdk-lib/aws-dynamodb';
import { Effect, PolicyStatement, Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';
import { Architecture, LayerVersion, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Bucket } from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';

export interface DeleteModelsApiProps {
  router: Resource;
  httpMethod: string;
  modelTable: Table;
  srcRoot: string;
  commonLayer: LayerVersion;
  s3Bucket: Bucket;
  logLevel: CfnParameter;
}

export class DeleteModelsApi {
  private readonly src: string;
  private readonly router: Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly modelTable: Table;
  private readonly layer: LayerVersion;
  private readonly baseId: string;
  private readonly s3Bucket: Bucket;
  private readonly logLevel: CfnParameter;
  public model: Model;
  public requestValidator: RequestValidator;

  constructor(scope: Construct, id: string, props: DeleteModelsApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.modelTable = props.modelTable;
    this.src = props.srcRoot;
    this.layer = props.commonLayer;
    this.s3Bucket = props.s3Bucket;
    this.logLevel = props.logLevel;
    this.model = this.createModel();
    this.requestValidator = this.createRequestValidator();

    this.deleteModelsApi();
  }

  private createModel(): Model {
    return new Model(
      this.scope,
      `${this.baseId}-model`,
      {
        restApi: this.router.api,
        modelName: this.baseId,
        description: `${this.baseId} Request Model`,
        schema: {
          schema: JsonSchemaVersion.DRAFT4,
          title: this.baseId,
          type: JsonSchemaType.OBJECT,
          properties: {
            model_id_list: {
              type: JsonSchemaType.ARRAY,
              items: {
                type: JsonSchemaType.STRING,
                minLength: 1,
              },
              minItems: 1,
              maxItems: 100,
            },
          },
          required: [
            'model_id_list',
          ],
        },
        contentType: 'application/json',
      });
  }

  private createRequestValidator() :RequestValidator {
    return new RequestValidator(
      this.scope,
      `${this.baseId}-del-model-validator`,
      {
        restApi: this.router.api,
        validateRequestBody: true,
      });
  }

  private deleteModelsApi() {

    const lambdaFunction = new PythonFunction(
      this.scope,
      `${this.baseId}-lambda`,
      {
        entry: `${this.src}/models`,
        architecture: Architecture.X86_64,
        runtime: Runtime.PYTHON_3_9,
        index: 'delete_models.py',
        handler: 'handler',
        timeout: Duration.seconds(900),
        role: this.iamRole(),
        memorySize: 1024,
        environment: {
          MODELS_TABLE: this.modelTable.tableName,
          S3_BUCKET_NAME: this.s3Bucket.bucketName,
          LOG_LEVEL: this.logLevel.valueAsString,
        },
        layers: [this.layer],
      });


    const lambdaIntegration = new LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.addMethod(
      this.httpMethod,
      lambdaIntegration,
      {
        apiKeyRequired: true,
        requestValidator: this.requestValidator,
        requestModels: {
          'application/json': this.model,
        },
      });

  }

  private iamRole(): Role {

    const newRole = new Role(
      this.scope,
      `${this.baseId}-role`,
      {
        assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
      },
    );

    newRole.addToPolicy(new PolicyStatement({
      actions: [
        // get model
        'dynamodb:GetItem',
        // delete model
        'dynamodb:DeleteItem',
      ],
      resources: [
        this.modelTable.tableArn,
      ],
    }));

    newRole.addToPolicy(new PolicyStatement({
      actions: [
        // list model objects by prefix
        's3:ListBucket',
        // delete model file
        's3:DeleteObject',
      ],
      resources: [
        `${this.s3Bucket.bucketArn}`,
        `${this.s3Bucket.bucketArn}/*`,
      ],
    }));

    newRole.addToPolicy(new PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'logs:CreateLogGroup',
        'logs:CreateLogStream',
        'logs:PutLogEvents',
      ],
      resources: [`arn:${Aws.PARTITION}:logs:${Aws.REGION}:${Aws.ACCOUNT_ID}:log-group:*:*`],
    }));

    return newRole;
  }
}
