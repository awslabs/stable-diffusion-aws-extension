import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, aws_lambda, Duration } from 'aws-cdk-lib';
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
import { ApiModels } from '../../shared/models';
import { SCHEMA_DATASET_NAME } from '../../shared/schema';

export interface DeleteDatasetsApiProps {
  router: Resource;
  httpMethod: string;
  datasetInfoTable: Table;
  datasetItemTable: Table;
  multiUserTable: Table;
  commonLayer: LayerVersion;
  s3Bucket: Bucket;
}

export class DeleteDatasetsApi {
  private readonly router: Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly datasetInfoTable: Table;
  private readonly datasetItemTable: Table;
  private readonly multiUserTable: Table;
  private readonly layer: LayerVersion;
  private readonly baseId: string;
  private readonly s3Bucket: Bucket;

  constructor(scope: Construct, id: string, props: DeleteDatasetsApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.datasetInfoTable = props.datasetInfoTable;
    this.datasetItemTable = props.datasetItemTable;
    this.multiUserTable = props.multiUserTable;
    this.layer = props.commonLayer;
    this.s3Bucket = props.s3Bucket;

    const lambdaFunction =this.apiLambda();

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
        requestValidator: this.createRequestValidator(),
        requestModels: {
          'application/json': this.createRequestBodyModel(),
        },
        operationName: 'DeleteDatasets',
        methodResponses: [
          ApiModels.methodResponses401(),
          ApiModels.methodResponses403(),
          ApiModels.methodResponses404(),
        ],
      });

  }

  private createRequestBodyModel(): Model {
    return new Model(
      this.scope,
      `${this.baseId}-model`,
      {
        restApi: this.router.api,
        modelName: this.baseId,
        description: `Request Model ${this.baseId}`,
        schema: {
          schema: JsonSchemaVersion.DRAFT7,
          title: this.baseId,
          type: JsonSchemaType.OBJECT,
          properties: {
            dataset_name_list: {
              type: JsonSchemaType.ARRAY,
              items: SCHEMA_DATASET_NAME,
              minItems: 1,
              maxItems: 10,
            },
          },
          required: [
            'dataset_name_list',
          ],
        },
        contentType: 'application/json',
      });
  }

  private createRequestValidator(): RequestValidator {
    return new RequestValidator(
      this.scope,
      `${this.baseId}-del-dataset-validator`,
      {
        restApi: this.router.api,
        validateRequestBody: true,
      });
  }

  private apiLambda() {
    return new PythonFunction(
      this.scope,
      `${this.baseId}-lambda`,
      {
        entry: '../middleware_api/datasets',
        architecture: Architecture.X86_64,
        runtime: Runtime.PYTHON_3_10,
        index: 'delete_datasets.py',
        handler: 'handler',
        timeout: Duration.seconds(900),
        role: this.iamRole(),
        memorySize: 2048,
        tracing: aws_lambda.Tracing.ACTIVE,
        environment: {
          DATASET_INFO_TABLE: this.datasetInfoTable.tableName,
          DATASET_ITEM_TABLE: this.datasetItemTable.tableName,
        },
        layers: [this.layer],
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
        // query dataset files
        'dynamodb:Query',
        // delete dataset
        'dynamodb:DeleteItem',
        // sacn users
        'dynamodb:Scan',
      ],
      resources: [
        this.datasetInfoTable.tableArn,
        this.datasetItemTable.tableArn,
        this.multiUserTable.tableArn,
      ],
    }));

    newRole.addToPolicy(new PolicyStatement({
      actions: [
        // list dataset items by prefix
        's3:ListBucket',
        // delete dataset file
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
