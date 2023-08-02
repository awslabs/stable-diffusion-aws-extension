import { aws_dynamodb, aws_dynamodb as dynamodb, RemovalPolicy } from 'aws-cdk-lib';
import { AttributeType } from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';

export class Database {
  public readonly modelTable: aws_dynamodb.Table;
  public readonly trainingTable: aws_dynamodb.Table;
  public readonly checkPointTable: aws_dynamodb.Table;
  public readonly datasetInfoTable: aws_dynamodb.Table;
  public readonly datasetItemTable: aws_dynamodb.Table;
  public readonly endpointDeploymentJobTable: aws_dynamodb.Table;
  public readonly inferenceJobTable: aws_dynamodb.Table;

  constructor(scope: Construct, baseId: string) {

    // Create DynamoDB table to store model job id
    this.modelTable = new dynamodb.Table(scope, `${baseId}-ModelTable`, {
      tableName: 'ModelTable',
      partitionKey: { name: 'id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    // Create DynamoDB table to store training job id
    this.trainingTable = new dynamodb.Table(scope, `${baseId}-TrainingTable`, {
      tableName: 'TrainingTable',
      partitionKey: { name: 'id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    this.checkPointTable = new dynamodb.Table(scope, `${baseId}-CheckpointTable`, {
      tableName: 'CheckpointTable',
      partitionKey: {
        name: 'id',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    this.datasetInfoTable = new dynamodb.Table(scope, `${baseId}-DatasetInfoTable`, {
      tableName: 'DatasetInfoTable',
      partitionKey: {
        name: 'dataset_name',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    this.datasetItemTable = new dynamodb.Table(scope, `${baseId}-DatasetItemTable`, {
      tableName: 'DatasetItemTable',
      partitionKey: {
        name: 'dataset_name',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'sort_key',
        type: AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    // create Dynamodb table to save the inference job data
    this.inferenceJobTable = new dynamodb.Table(scope, `${baseId}-InferenceJobTable`,
      {
        tableName: 'SDInferenceJobTable',
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: RemovalPolicy.DESTROY,
        partitionKey: {
          name: 'InferenceJobId',
          type: dynamodb.AttributeType.STRING,
        },
        pointInTimeRecovery: true,
      },
    );

    // create Dynamodb table to save the inference job data
    this.endpointDeploymentJobTable = new dynamodb.Table(scope, `${baseId}-EndpointDeploymentJob`,
      {
        tableName: 'SDEndpointDeploymentJobTable',
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: RemovalPolicy.DESTROY,
        partitionKey: {
          name: 'EndpointDeploymentJobId',
          type: dynamodb.AttributeType.STRING,
        },
        pointInTimeRecovery: true,
      },
    );
  }

}