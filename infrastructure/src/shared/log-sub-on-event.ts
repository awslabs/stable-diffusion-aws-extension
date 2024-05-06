import * as zlib from "zlib";

export async function handler(event: Object, context: Object, callback: CallableFunction) {

  // if it's from CloudWatch Subscription filters
  if (event.awslogs) {

    let payload = Buffer.from(event.awslogs.data, 'base64');

    event.awslogs = JSON.parse(zlib.gunzipSync(payload));

    const {logGroup, logStream, logEvents} = event.awslogs;

    for (let i in logEvents) {
      let logEvent = logEvents[i];
      console.log(logGroup);
      console.log(logStream);
      console.log(logEvent);
    }


  }


  return {}
}
