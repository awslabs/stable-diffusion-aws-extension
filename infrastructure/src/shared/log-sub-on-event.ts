import * as zlib from "zlib";
import {DynamoDB} from "aws-sdk";

interface Event {
    awslogs: {
        data: string;
    };
}

interface Log {
    logGroup: string;
    logStream: string;
    logEvents: [];
}

export async function handler(event: Event, context: Object) {

  // if it's from CloudWatch Subscription filters
  if (event.awslogs) {
    let lists = [];

    let payload = Buffer.from(event.awslogs.data, 'base64');

    const log: Log = JSON.parse(zlib.gunzipSync(payload).toString());

    const {logGroup, logStream, logEvents} = log;

    for (let i in logEvents) {

      let {id, timestamp, message} = logEvents[i];

      const Item = {
        id,
        logGroup,
        logStream,
        timestamp,
        message
      };

      lists.push({
        PutRequest: {
          Item
        }
      });

    }

    await putItems(lists);



  }

  return {}
}

export async function putItems(list: Array<Object>) {

  const batch = 25;

  let items = [];

  for (let i in list) {
    items.push(list[i]);
    if (items.length === batch) {
      await put(items);
      items = [];
    }
  }

  await put(items);
}

export async function put(items: Array<Object>) {
  const table = 'EsdLogSubTable';
  if (items.length === 0) {
    return;
  }

  console.log(JSON.stringify({table, items}, null, "  "));

  const params = {
    RequestItems: {
      [table]: items
    },
  };

  const dynamoDb = new DynamoDB.DocumentClient();

  const res = dynamoDb.batchWrite(params, function (err, data) {
    if (err) {
      console.log({table, error: err});
      return err;
    }

    console.log({table, succeed: data});
    return data;
  });

  console.log(await res.promise());

}

