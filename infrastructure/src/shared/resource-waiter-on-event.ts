import { DescribeTableCommand, DynamoDBClient } from '@aws-sdk/client-dynamodb';

const ddbClient = new DynamoDBClient({});
const timeoutMinutesInMilliseconds = 13 * 60 * 1000;

interface Event {
  RequestType: string;
  PhysicalResourceId: string;
  ResourceProperties: {
    ServiceToken: string;
    apiUrl: string;
    apiKey: string;
    name: string;
  };
}

export async function handler(event: Event, context: Object) {

  console.log(JSON.stringify(event));
  console.log(JSON.stringify(context));

  const allow_types = ['Create', 'Update'];

  if (allow_types.includes(event.RequestType)) {
    await waitApiReady(event, 'ping');
    await waitApiReady(event, 'api');
    await waitApiReady(event, 'roles');
    await waitApiReady(event, 'users');
    await waitTableIndexReady(event, 'SDInferenceJobTable', 'taskType', 'createTime');
    await waitTableIndexReady(event, 'SDEndpointDeploymentJobTable', 'endpoint_name', 'startTime');
  }

  return response(event, true);

}


async function waitApiReady(event: Event, path: string) {
  const lambdaStartTime = Date.now();
  const startCheckTime = Date.now();

  while (true) {

    const currentTime = Date.now();

    if (currentTime - lambdaStartTime > timeoutMinutesInMilliseconds) {
      console.log(`${event.ResourceProperties.name} Time exceeded 13 minutes. Exiting loop.`);
      break;
    }

    try {
      const url = `${event.ResourceProperties.apiUrl}/${path}`;
      console.log(`${event.ResourceProperties.name} Checking API readiness ${url}...`);

      const resp = await fetch(url, {
        method: 'GET',
        headers: {
          'x-api-key': event.ResourceProperties.apiKey,
        },
      });

      if (resp.status === 200) {
        console.log(`${event.ResourceProperties.name} Received 200 after ${(currentTime - startCheckTime) / 1000} seconds!`);
        break;
      }

      console.log(`${event.ResourceProperties.name} Did not receive 200 from API. Checking again in 3 seconds...`);
      await new Promise(resolve => setTimeout(resolve, 3000));

    } catch (error) {
      console.error(error);
      await new Promise(resolve => setTimeout(resolve, 3000));
    }
  }

}


async function waitTableIndexReady(event: Event, tableName: string, pk: string, sk: string) {
  const lambdaStartTime = Date.now();
  const indexName = `${pk}-${sk}-index`;

  const startCheckTime = Date.now();

  while (true) {
    const currentTime = Date.now();

    if (currentTime - lambdaStartTime > timeoutMinutesInMilliseconds) {
      console.log(`${event.ResourceProperties.name} Time exceeded 13 minutes. Exiting loop.`);
      break;
    }

    const data = await ddbClient.send(new DescribeTableCommand({ TableName: tableName }));
    const index = data.Table?.GlobalSecondaryIndexes?.find(idx => idx.IndexName === indexName);

    if (!index) {
      throw new Error(`${event.ResourceProperties.name} ${indexName} does not exist on table ${tableName}`);
    }

    if (index.IndexStatus === 'ACTIVE') {
      console.log(`${event.ResourceProperties.name} ${indexName} is active after ${(currentTime - startCheckTime) / 1000} seconds!`);
      break;
    } else if (index.IndexStatus === 'CREATING') {
      console.log(`${event.ResourceProperties.name} ${indexName} is Creating, check again in 2 second...`);
    } else {
      throw new Error(`${event.ResourceProperties.name} ${indexName} is in unknown state: ${index.IndexStatus}`);
    }

    await new Promise(r => setTimeout(r, 2000));

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


