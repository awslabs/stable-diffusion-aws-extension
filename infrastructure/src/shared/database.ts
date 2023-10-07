import { aws_dynamodb, CfnCondition, Fn, RemovalPolicy } from 'aws-cdk-lib';
import { Attribute, AttributeType } from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';


export class Database {
  [index: string]: aws_dynamodb.Table;

  constructor(scope: Construct, baseId: string, useExist: string) {
    interface tableProperties {
      partitionKey: Attribute;
      sortKey?: Attribute;
    }

    const tables: {[key: string]: tableProperties} = {
      ModelTable: {
        partitionKey: { name: 'id', type: aws_dynamodb.AttributeType.STRING },
      },
      TrainingTable: {
        partitionKey: { name: 'id', type: aws_dynamodb.AttributeType.STRING },
      },
      CheckpointTable: {
        partitionKey: {
          name: 'id',
          type: aws_dynamodb.AttributeType.STRING,
        },
      },
      DatasetInfoTable: {
        partitionKey: {
          name: 'dataset_name',
          type: aws_dynamodb.AttributeType.STRING,
        },
      },
      DatasetItemTable: {
        partitionKey: {
          name: 'dataset_name',
          type: aws_dynamodb.AttributeType.STRING,
        },
        sortKey: {
          name: 'sort_key',
          type: AttributeType.STRING,
        },
      },
      SDInferenceJobTable: {
        partitionKey: {
          name: 'InferenceJobId',
          type: aws_dynamodb.AttributeType.STRING,
        },
      },
      SDEndpointDeploymentJobTable: {
        partitionKey: {
          name: 'EndpointDeploymentJobId',
          type: aws_dynamodb.AttributeType.STRING,
        },
      },
      MultiUserTable: {
        partitionKey: {
          name: 'kind',
          type: aws_dynamodb.AttributeType.STRING,
        },
        sortKey: {
          name: 'sort_key',
          type: AttributeType.STRING,
        },
      },
    };

    const shouldCreateDDBTableCondition = new CfnCondition(
      scope,
      `${this.id}-shouldCreateDDBTable`,
      {
        expression: Fn.conditionEquals(useExist, 'no'),
      },
    );

    // Create DynamoDB table to store model job id
    for (let key in tables) {
      const val = tables[key];

      const newTable = new aws_dynamodb.Table(scope, `${baseId}-new-${key}`, {
        tableName: key,
        partitionKey: val.partitionKey,
        billingMode: aws_dynamodb.BillingMode.PAY_PER_REQUEST,
        sortKey: val.sortKey,
        removalPolicy: RemovalPolicy.RETAIN,
      });

      (newTable.node.defaultChild as aws_dynamodb.CfnTable).cfnOptions.condition = shouldCreateDDBTableCondition;

      this[key.charAt(0).toLocaleLowerCase() + key.slice(1)] = <aws_dynamodb.Table> aws_dynamodb.Table.fromTableName(scope, `${baseId}-${key}`, key);
    }
  }
}