import * as zlib from "zlib";

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

      lists.push(Item);
    }

    console.log(lists);

  }

  return {}
}

