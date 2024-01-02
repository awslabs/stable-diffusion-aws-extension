import { PythonFunction, PythonFunctionProps } from '@aws-cdk/aws-lambda-python-alpha';
import {
  Aws,
  aws_apigateway as apigw,
  aws_apigateway,
  aws_dynamodb,
  aws_iam,
  aws_lambda,
  aws_s3,
  CfnParameter,
  Duration
} from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, Model, RequestValidator } from 'aws-cdk-lib/aws-apigateway';
import { MethodOptions } from 'aws-cdk-lib/aws-apigateway/lib/method';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';

export interface CreateTrainingJobApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  modelTable: aws_dynamodb.Table;
  trainTable: aws_dynamodb.Table;
  multiUserTable: aws_dynamodb.Table;
  srcRoot: string;
  s3Bucket: aws_s3.Bucket;
  commonLayer: aws_lambda.LayerVersion;
  checkpointTable: aws_dynamodb.Table;
  logLevel: CfnParameter;
}

export class CreateTrainingJobApi {

  private readonly id: string;
  private readonly scope: Construct;
  private readonly srcRoot: string;
  private readonly modelTable: aws_dynamodb.Table;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly s3Bucket: aws_s3.Bucket;
  private readonly httpMethod: string;
  private readonly router: aws_apigateway.Resource;
  private readonly trainTable: aws_dynamodb.Table;
  private readonly checkpointTable: aws_dynamodb.Table;
  private readonly multiUserTable: aws_dynamodb.Table;
  private readonly logLevel: CfnParameter;

  constructor(scope: Construct, id: string, props: CreateTrainingJobApiProps) {
    this.id = id;
    this.scope = scope;
    this.srcRoot = props.srcRoot;
    this.checkpointTable = props.checkpointTable;
    this.multiUserTable = props.multiUserTable;
    this.modelTable = props.modelTable;
    this.layer = props.commonLayer;
    this.s3Bucket = props.s3Bucket;
    this.httpMethod = props.httpMethod;
    this.router = props.router;
    this.trainTable = props.trainTable;
    this.logLevel = props.logLevel;

    this.createTrainJobLambda();
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
        this.modelTable.tableArn,
        this.trainTable.tableArn,
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

  private createTrainJobLambda(): aws_lambda.IFunction {
    const lambdaFunction = new PythonFunction(this.scope, `${this.id}-lambda`, <PythonFunctionProps>{
      entry: `${this.srcRoot}/trainings`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_9,
      index: 'create_training_job.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.lambdaRole(),
      memorySize: 1024,
      environment: {
        S3_BUCKET: this.s3Bucket.bucketName,
        TRAIN_TABLE: this.trainTable.tableName,
        MODEL_TABLE: this.modelTable.tableName,
        CHECKPOINT_TABLE: this.checkpointTable.tableName,
        MULTI_USER_TABLE: this.multiUserTable.tableName,
        LOG_LEVEL: this.logLevel.valueAsString,
      },
      layers: [this.layer],
    });

    const createTrainJobIntegration = new apigw.LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    const requestModel = new Model(this.scope, `${this.id}-model`, {
      restApi: this.router.api,
      modelName: this.id,
      description: `${this.id} Request Model`,
      schema: {
        schema: JsonSchemaVersion.DRAFT4,
        title: this.id,
        type: JsonSchemaType.OBJECT,
        properties: {
          train_type: {
            type: JsonSchemaType.STRING,
            minLength: 1,
          },
          model_id: {
            type: JsonSchemaType.STRING,
            minLength: 1,
          },
          filenames: {
            type: JsonSchemaType.ARRAY,
            maxItems: 1,
          },
          params: {
            type: JsonSchemaType.OBJECT,
          },
        },
        required: [
          'train_type',
          'model_id',
          'filenames',
          'params',
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


    this.router.addMethod(this.httpMethod, createTrainJobIntegration, <MethodOptions>{
      apiKeyRequired: true,
      requestValidator,
      requestModels: {
        'application/json': requestModel,
      },
    });

    return lambdaFunction;
  }

}
