import { DescribeTableCommand, DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { INFER_INDEX_NAME } from './resource-provider-on-event';

const ddbClient = new DynamoDBClient({});

interface Event {
  RequestType: string;
  PhysicalResourceId: string;
}

export async function handler(event: Event, context: Object) {

  console.log(JSON.stringify(event));
  console.log(JSON.stringify(context));

  const allow_types = ['Create', 'Update'];

  if (allow_types.includes(event.RequestType)) {
    await waitTableIndexReady('SDInferenceJobTable', INFER_INDEX_NAME);
  }

  return response(event, true);

}


async function waitTableIndexReady(tableName: string, indexName: string) {
  const params = {
    TableName: tableName,
  };

  const command = new DescribeTableCommand(params);
  while (true) {
    const data = await ddbClient.send(command);
    const index = data.Table?.GlobalSecondaryIndexes?.find(idx => idx.IndexName === indexName);

    if (!index) {
      throw new Error(`Index ${indexName} does not exist on table ${tableName}`);
    }

    if (index.IndexStatus === 'ACTIVE') {
      console.log(`Index ${indexName} is active and ready to use.`);
      break;
    } else if (index.IndexStatus === 'CREATING') {
      console.log(`Index ${indexName} is still being created. Checking again in 1 second...`);
    } else {
      throw new Error(`Index ${indexName} is in unknown state: ${index.IndexStatus}`);
    }

    await new Promise(r => setTimeout(r, 1000));
  }
}


export interface ResourceWaiterResponse {
  Result: string;
}

function response(event: Event, isComplete: boolean) {
  return {
    PhysicalResourceId: event.PhysicalResourceId,
    IsComplete: isComplete,
    Data: {
      Result: 'Success',
    } as ResourceWaiterResponse,
  };
}


