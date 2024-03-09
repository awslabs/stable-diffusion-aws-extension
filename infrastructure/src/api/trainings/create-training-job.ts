import { PythonFunction, PythonFunctionProps } from '@aws-cdk/aws-lambda-python-alpha';
import {
  Aws,
  aws_apigateway as apigw,
  aws_apigateway,
  aws_dynamodb,
  aws_iam,
  aws_lambda,
  aws_s3,
  aws_sns,
  CfnParameter,
  Duration,
} from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, Model, RequestValidator } from 'aws-cdk-lib/aws-apigateway';
import { MethodOptions } from 'aws-cdk-lib/aws-apigateway/lib/method';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { ResourceProvider } from '../../shared/resource-provider';

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
  userTopic: aws_sns.Topic;
  logLevel: CfnParameter;
  ecr_image_tag: CfnParameter;
  resourceProvider: ResourceProvider;
}

export class CreateTrainingJobApi {

  public model: Model;
  public requestValidator: RequestValidator;
  private readonly id: string;
  private readonly scope: Construct;
  private readonly ecr_image_tag: CfnParameter;
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
  private readonly sagemakerTrainRole: aws_iam.Role;
  private readonly userSnsTopic: aws_sns.Topic;
  private readonly instanceType: string = 'ml.g4dn.2xlarge';

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
    this.model = this.createModel();
    this.requestValidator = this.createRequestValidator();
    this.sagemakerTrainRole = this.sageMakerTrainRole();
    this.userSnsTopic = props.userTopic;
    this.ecr_image_tag = props.ecr_image_tag;

    this.createTrainJobLambda();
  }


  private sageMakerTrainRole(): aws_iam.Role {
    const sagemakerRole = new aws_iam.Role(this.scope, `${this.id}-train-role`, {
      assumedBy: new aws_iam.ServicePrincipal('sagemaker.amazonaws.com'),
    });
    sagemakerRole.addManagedPolicy(aws_iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSageMakerFullAccess'));

    sagemakerRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        's3:GetObject',
        's3:PutObject',
      ],
      resources: [
        `${this.s3Bucket.bucketArn}/*`,
        `arn:${Aws.PARTITION}:s3:::*SageMaker*`,
        `arn:${Aws.PARTITION}:s3:::*Sagemaker*`,
        `arn:${Aws.PARTITION}:s3:::*sagemaker*`,
      ],
    }));

    sagemakerRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'kms:Decrypt',
      ],
      resources: ['*'],
    }));

    return sagemakerRole;
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
        'sagemaker:CreateTrainingJob',
      ],
      resources: [`arn:${Aws.PARTITION}:sagemaker:${Aws.REGION}:${Aws.ACCOUNT_ID}:training-job/*`],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'iam:PassRole',
      ],
      resources: [this.sagemakerTrainRole.roleArn],
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

  private createModel(): Model {
    return new Model(this.scope, `${this.id}-model`, {
      restApi: this.router.api,
      modelName: this.id,
      description: `${this.id} Request Model`,
      schema: {
        schema: JsonSchemaVersion.DRAFT4,
        title: this.id,
        type: JsonSchemaType.OBJECT,
        properties: {
          params: {
            type: JsonSchemaType.OBJECT,
          },
          lora_train_type: {
            type: JsonSchemaType.STRING,
            minLength: 1,
          },
        },
        required: [
          'params',
        ],
      },
      contentType: 'application/json',
    });
  }

  private createRequestValidator(): RequestValidator {
    return new RequestValidator(
      this.scope,
      `${this.id}-create-train-validator`,
      {
        restApi: this.router.api,
        validateRequestBody: true,
      });
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
        INSTANCE_TYPE: this.instanceType,
        TRAIN_JOB_ROLE: this.sagemakerTrainRole.roleArn,
        TRAIN_ECR_URL: `366590864501.dkr.ecr.${Aws.REGION}.${Aws.URL_SUFFIX}/esd-training:${this.ecr_image_tag.valueAsString}`,
        USER_EMAIL_TOPIC_ARN: this.userSnsTopic.topicArn,
      },
      layers: [this.layer],
    });

    const createTrainJobIntegration = new apigw.LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.addMethod(this.httpMethod, createTrainJobIntegration, <MethodOptions>{
      apiKeyRequired: true,
      requestValidator: this.requestValidator,
      requestModels: {
        'application/json': this.model,
      },
    });

    return lambdaFunction;
  }

}
