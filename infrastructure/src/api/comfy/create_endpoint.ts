import { Aws, aws_dynamodb, aws_iam, aws_lambda, aws_s3, aws_sagemaker, aws_sqs, CfnParameter } from 'aws-cdk-lib';
import { Effect, ServicePrincipal } from 'aws-cdk-lib/aws-iam';
import { CfnEndpointConfigProps, CfnEndpointProps, CfnModelProps } from 'aws-cdk-lib/aws-sagemaker';
import { Construct } from 'constructs';
import { ResourceProvider } from '../../shared/resource-provider';

export interface CreateSageMakerEndpointProps {
  dockerImageUrl: string;
  modelDataUrl: string;
  s3Bucket: aws_s3.Bucket;
  machineType: string;
  rootSrc: string;
  configTable: aws_dynamodb.Table;
  modelTable: aws_dynamodb.Table;
  syncTable: aws_dynamodb.Table;
  commonLayer: aws_lambda.LayerVersion;
  queue: aws_sqs.Queue;
  resourceProvider: ResourceProvider;
  logLevel: CfnParameter;
}

export class CreateSageMakerEndpoint {

  private readonly id: string;
  public model: aws_sagemaker.CfnModel;
  public modelConfig: aws_sagemaker.CfnEndpointConfig;
  public modelEndpoint: aws_sagemaker.CfnEndpoint;
  private configTable: aws_dynamodb.Table;
  private syncTable: aws_dynamodb.Table;
  private queue: aws_sqs.Queue;

  constructor(scope: Construct, id: string, props: CreateSageMakerEndpointProps) {
    this.id = id;
    this.queue = props.queue;
    this.configTable = props.configTable;
    this.syncTable = props.syncTable;

    const role = this.sagemakerRole(scope);

    this.model = new aws_sagemaker.CfnModel(scope, `${this.id}-model`, <CfnModelProps>{
      executionRoleArn: role.roleArn,
      modelName: `${this.id}-model`,
      primaryContainer: {
        image: props.dockerImageUrl,
        // modelDataUrl: props.modelDataUrl,
        environment: {
          AWS_DEFAULT_REGION: Aws.REGION,
          BUCKET_NAME: props.s3Bucket.bucketName,
        },
      },
    });

    this.model.node.addDependency(role);

    this.modelConfig = new aws_sagemaker.CfnEndpointConfig(scope, `${this.id}-model-config`, <CfnEndpointConfigProps>{
      endpointConfigName: `${this.id}-config`,
      productionVariants: [
        {
          modelName: this.model.modelName,
          initialVariantWeight: 1.0,
          variantName: 'main',
          initialInstanceCount: 1,
          instanceType: props.machineType,
        },
      ],
    });

    this.modelConfig.node.addDependency(this.model);

    this.modelEndpoint = new aws_sagemaker.CfnEndpoint(scope, `${this.id}-endpoint`, <CfnEndpointProps>{
      endpointConfigName: this.modelConfig.endpointConfigName,
      endpointName: `${this.id}-endpoint`,
    });
    this.modelEndpoint.node.addDependency(this.modelConfig);
  }

  private sagemakerRole(scope: Construct): aws_iam.Role {
    const sagemakerRole = new aws_iam.Role(scope, `${this.id}-endpoint-role`, {
      assumedBy: new ServicePrincipal('sagemaker.amazonaws.com'),
    });
    sagemakerRole.addManagedPolicy(aws_iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSageMakerFullAccess'));

    sagemakerRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        's3:GetObject',
        's3:ListBucket',
        's3:PutObject',
        's3:GetObject',
      ],
      resources: ['arn:aws:s3:::*'],
    }));

    sagemakerRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'sqs:SendMessage',
      ],
      resources: [this.queue.queueArn],
    }));

    sagemakerRole.addToPolicy(new aws_iam.PolicyStatement({
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
        this.syncTable.tableArn,
        this.configTable.tableArn,
      ],
    }));

    sagemakerRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'sagemaker:InvokeEndpointAsync',
        'sagemaker:InvokeEndpoint',
      ],
      resources: [`arn:${Aws.PARTITION}:sagemaker:${Aws.REGION}:${Aws.ACCOUNT_ID}:endpoint/*`],
    }));

    sagemakerRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'logs:CreateLogGroup',
        'logs:CreateLogStream',
        'logs:PutLogEvents',
      ],
      resources: ['*'],
    }));

    sagemakerRole.addToPolicy(new aws_iam.PolicyStatement({
      actions: [
        'ecr:GetAuthorizationToken',
        'ecr:BatchCheckLayerAvailability',
        'ecr:GetDownloadUrlForLayer',
        'ecr:GetRepositoryPolicy',
        'ecr:DescribeRepositories',
        'ecr:ListImages',
        'ecr:DescribeImages',
        'ecr:BatchGetImage',
        'ecr:InitiateLayerUpload',
        'ecr:UploadLayerPart',
        'ecr:CompleteLayerUpload',
        'ecr:PutImage',
        'iam:CreateServiceLinkedRole',
        'iam:PassRole',
        'sts:AssumeRole',
      ],
      resources: ['*'],
    }),
    );

    return sagemakerRole;
  }
}
