import { aws_dynamodb } from 'aws-cdk-lib';
import { Attribute, AttributeType } from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';
import { ResourceProvider } from './resource-provider';


export class Database {
  [index: string]: aws_dynamodb.Table;

  constructor(scope: Construct, baseId: string, resourceProvider: ResourceProvider) {
    interface tableProperties {
      partitionKey: Attribute;
      sortKey?: Attribute;
    }

    const tables: { [key: string]: tableProperties } = {
      ModelTable: {
        partitionKey: {
          name: 'id',
          type: aws_dynamodb.AttributeType.STRING,
        },
      },
      TrainingTable: {
        partitionKey: {
          name: 'id',
          type: aws_dynamodb.AttributeType.STRING,
        },
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


    for (let key in tables) {
      const tableName = key.charAt(0).toLocaleLowerCase() + key.slice(1);
      this[tableName] = <aws_dynamodb.Table>aws_dynamodb.Table.fromTableName(scope, `${baseId}-${key}`, key);
      this[tableName].node.addDependency(resourceProvider.resources);
    }

  }
}
