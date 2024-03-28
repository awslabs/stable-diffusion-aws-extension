import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Aws, aws_apigateway, aws_dynamodb, aws_iam, aws_lambda, aws_s3, aws_sns, Duration } from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, Model, RequestValidator } from 'aws-cdk-lib/aws-apigateway';
import { MethodOptions } from 'aws-cdk-lib/aws-apigateway/lib/method';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { ICfnRuleConditionExpression } from 'aws-cdk-lib/core/lib/cfn-condition';
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
  datasetInfoTable: aws_dynamodb.Table;
  userTopic: aws_sns.Topic;
  resourceProvider: ResourceProvider;
  accountId: ICfnRuleConditionExpression;
}

export class CreateTrainingJobApi {

  public model: Model;
  public requestValidator: RequestValidator;
  private readonly id: string;
  private readonly scope: Construct;
  private readonly props: CreateTrainingJobApiProps;
  private readonly sagemakerTrainRole: aws_iam.Role;
  private readonly instanceType: string = 'ml.g4dn.2xlarge';

  constructor(scope: Construct, id: string, props: CreateTrainingJobApiProps) {
    this.id = id;
    this.scope = scope;
    this.props = props;
    this.model = this.createModel();
    this.requestValidator = this.createRequestValidator();
    this.sagemakerTrainRole = this.sageMakerTrainRole();

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
        `${this.props.s3Bucket.bucketArn}/*`,
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
        this.props.modelTable.tableArn,
        this.props.trainTable.tableArn,
        this.props.checkpointTable.tableArn,
        this.props.multiUserTable.tableArn,
        this.props.datasetInfoTable.tableArn,
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
        's3:CreateBucket',
      ],
      resources: [`${this.props.s3Bucket.bucketArn}/*`,
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
      restApi: this.props.router.api,
      modelName: this.id,
      description: `${this.id} Request Model`,
      schema: {
        schema: JsonSchemaVersion.DRAFT4,
        title: this.id,
        type: JsonSchemaType.OBJECT,
        properties: {
          lora_train_type: {
            type: JsonSchemaType.STRING,
            minLength: 1,
          },
          params: {
            type: JsonSchemaType.OBJECT,
            properties: {
              training_params: {
                type: JsonSchemaType.OBJECT,
                properties: {
                  training_instance_type: {
                    type: JsonSchemaType.STRING,
                  },
                  model: {
                    type: JsonSchemaType.STRING,
                  },
                  dataset: {
                    type: JsonSchemaType.STRING,
                  },
                  fm_type: {
                    type: JsonSchemaType.STRING,
                  },
                },
                required: [
                  'training_instance_type',
                  'model',
                  'dataset',
                  'fm_type',
                ],
              },
              config_params: {
                type: JsonSchemaType.OBJECT,
                properties: {
                  saving_arguments: {
                    type: JsonSchemaType.OBJECT,
                    properties: {
                      output_name: {
                        type: JsonSchemaType.STRING,
                      },
                      save_every_n_epochs: {
                        type: JsonSchemaType.INTEGER,
                      },
                    },
                    required: ['output_name', 'save_every_n_epochs'],
                  },
                  training_arguments: {
                    type: JsonSchemaType.OBJECT,
                    properties: {
                      max_train_epochs: {
                        type: JsonSchemaType.INTEGER,
                      },
                    },
                    required: ['max_train_epochs'],
                  },
                },
                required: [
                  'saving_arguments',
                  'training_arguments',
                ],
              },
            },
            required: [
              'training_params',
              'config_params',
            ],
          },
        },
        required: [
          'lora_train_type',
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
        restApi: this.props.router.api,
        validateRequestBody: true,
      });
  }

  private createTrainJobLambda(): aws_lambda.IFunction {
    const lambdaFunction = new PythonFunction(this.scope, `${this.id}-lambda`, {
      entry: `${this.props.srcRoot}/trainings`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'create_training_job.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.lambdaRole(),
      memorySize: 4089,
      tracing: aws_lambda.Tracing.ACTIVE,
      environment: {
        TRAIN_TABLE: this.props.trainTable.tableName,
        MODEL_TABLE: this.props.modelTable.tableName,
        DATASET_INFO_TABLE: this.props.datasetInfoTable.tableName,
        CHECKPOINT_TABLE: this.props.checkpointTable.tableName,
        INSTANCE_TYPE: this.instanceType,
        TRAIN_JOB_ROLE: this.sagemakerTrainRole.roleArn,
        TRAIN_ECR_URL: `${this.props.accountId.toString()}.dkr.ecr.${Aws.REGION}.${Aws.URL_SUFFIX}/esd-training:kohya-65bf90a`,
        USER_EMAIL_TOPIC_ARN: this.props.userTopic.topicArn,
      },
      layers: [this.props.commonLayer],
    });

    const createTrainJobIntegration = new aws_apigateway.LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.props.router.addMethod(this.props.httpMethod, createTrainJobIntegration, <MethodOptions>{
      apiKeyRequired: true,
      requestValidator: this.requestValidator,
      requestModels: {
        $default: this.model,
      },
    });

    return lambdaFunction;
  }

}
