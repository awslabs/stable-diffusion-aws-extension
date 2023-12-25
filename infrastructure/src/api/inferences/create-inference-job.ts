import { PythonFunction, PythonFunctionProps } from '@aws-cdk/aws-lambda-python-alpha';
import {
  Aws,
  aws_apigateway as apigw,
  aws_apigateway,
  aws_dynamodb,
  aws_iam,
  aws_lambda,
  aws_s3,
  Duration
} from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, Model, RequestValidator } from 'aws-cdk-lib/aws-apigateway';
import { MethodOptions } from 'aws-cdk-lib/aws-apigateway/lib/method';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';

export interface CreateInferenceJobApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  endpointDeploymentTable: aws_dynamodb.Table;
  inferenceJobTable: aws_dynamodb.Table;
  srcRoot: string;
  s3Bucket: aws_s3.Bucket;
  commonLayer: aws_lambda.LayerVersion;
  checkpointTable: aws_dynamodb.Table;
  multiUserTable: aws_dynamodb.Table;
}

export class CreateInferenceJobApi {

  private readonly id: string;
  private readonly scope: Construct;
  private readonly srcRoot: string;
  private readonly endpointDeploymentTable: aws_dynamodb.Table;
  private readonly inferenceJobTable: aws_dynamodb.Table;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly s3Bucket: aws_s3.Bucket;
  private readonly httpMethod: string;
  private readonly router: aws_apigateway.Resource;
  private readonly checkpointTable: aws_dynamodb.Table;
  private readonly multiUserTable: aws_dynamodb.Table;

  constructor(scope: Construct, id: string, props: CreateInferenceJobApiProps) {
    this.id = id;
    this.scope = scope;
    this.srcRoot = props.srcRoot;
    this.checkpointTable = props.checkpointTable;
    this.multiUserTable = props.multiUserTable;
    this.endpointDeploymentTable = props.endpointDeploymentTable;
    this.inferenceJobTable = props.inferenceJobTable;
    this.layer = props.commonLayer;
    this.s3Bucket = props.s3Bucket;
    this.httpMethod = props.httpMethod;
    this.router = props.router;

    this.createInferenceJobLambda();
  }

  private lambdaRole(): aws_iam.Role {
    const newRole = new aws_iam.Role(this.scope, `${this.id}-role`, {
      assumedBy: new aws_iam.ServicePrincipal('lambda.amazonaws.com'),
    });
    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'dynamodb:BatchGetItem',
        'dynamodb:GetItem',
        'dynamodb:Scan',
        'dynamodb:Query',
        'dynamodb:BatchWriteItem',
        'dynamodb:PutItem',
        'dynamodb:UpdateItem',
        'dynamodb:DeleteItem',
      ],
      resources: [
        this.inferenceJobTable.tableArn,
        this.endpointDeploymentTable.tableArn,
        this.checkpointTable.tableArn,
        this.multiUserTable.tableArn,
      ],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        's3:GetObject',
        's3:PutObject',
        's3:DeleteObject',
        's3:ListBucket',
      ],
      resources: [`${this.s3Bucket.bucketArn}/*`,
        `arn:${Aws.PARTITION}:s3:::*SageMaker*`,
        `arn:${Aws.PARTITION}:s3:::*Sagemaker*`,
        `arn:${Aws.PARTITION}:s3:::*sagemaker*`],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'logs:CreateLogGroup',
        'logs:CreateLogStream',
        'logs:PutLogEvents',
        'kms:Decrypt',
      ],
      resources: ['*'],
    }));

    return newRole;
  }

  private createInferenceJobLambda(): aws_lambda.IFunction {
    const lambdaFunction = new PythonFunction(this.scope, `${this.id}-lambda`, <PythonFunctionProps>{
      entry: `${this.srcRoot}/inferences`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_9,
      index: 'create_inference_job.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.lambdaRole(),
      memorySize: 1024,
      environment: {
        S3_BUCKET: this.s3Bucket.bucketName,
        DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME: this.endpointDeploymentTable.tableName,
        DDB_INFERENCE_TABLE_NAME: this.inferenceJobTable.tableName,
        CHECKPOINT_TABLE: this.checkpointTable.tableName,
        MULTI_USER_TABLE: this.multiUserTable.tableName,
      },
      layers: [this.layer],
    });

    const requestModel = new Model(this.scope, `${this.id}-model`, {
      restApi: this.router.api,
      modelName: this.id,
      description: `${this.id} Request Model`,
      schema: {
        schema: JsonSchemaVersion.DRAFT4,
        title: this.id,
        type: JsonSchemaType.OBJECT,
        properties: {
          task_type: {
            type: JsonSchemaType.STRING,
            minLength: 1,
          },
          models: {
            type: JsonSchemaType.OBJECT,
            properties: {
              embeddings: {
                type: JsonSchemaType.ARRAY,
              },
            },
          },
        },
        required: [
          'task_type',
          'models',
        ],
      },
      contentType: 'application/json',
    });

    const requestValidator = new RequestValidator(
      this.scope,
      `${this.id}-validator`,
      {
        restApi: this.router.api,
        requestValidatorName: this.id,
        validateRequestBody: true,
      });

    const createInferenceJobIntegration = new apigw.LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );
    this.router.addMethod(this.httpMethod, createInferenceJobIntegration, <MethodOptions>{
      apiKeyRequired: true,
      requestValidator,
      requestModels: {
        'application/json': requestModel,
      },
    });
    return lambdaFunction;
  }
}
