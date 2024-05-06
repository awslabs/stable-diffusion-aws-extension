import * as zlib from "zlib";
import {DynamoDB} from "aws-sdk";
const TABLE_NAME = process.env.TABLE_NAME || "";
export async function handler(event: Object, context: Object, callback: CallableFunction) {

  // if it's from CloudWatch Subscription filters
  if (event.awslogs) {
    let lists = [];

    let payload = Buffer.from(event.awslogs.data, 'base64');

    event.awslogs = JSON.parse(zlib.gunzipSync(payload));

    const {logGroup, logStream, logEvents} = event.awslogs;

    for (let i in logEvents) {
      let logEvent = logEvents[i];

      let {id, timestamp, message} = logEvents[i];

      console.log(logGroup);
      console.log(logStream);
      console.log(logEvent);

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


export async function putItems(list) {



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

export async function put(items) {

  if (items.length === 0) {
    return;
  }

  console.log(JSON.stringify({TABLE_NAME, items}, null, "  "));

  const params = {
    RequestItems: {
      [TABLE_NAME]: items
    },
  };

  const dynamoDb = new DynamoDB.DocumentClient();

  const res = await dynamoDb.batchWrite(params, function (err, data) {
    if (err) {
      console.log({table, error: err});
      return err;
    }

    console.log({table, succeed: data});
    return data;
  });

  console.log(await res.promise());

}
