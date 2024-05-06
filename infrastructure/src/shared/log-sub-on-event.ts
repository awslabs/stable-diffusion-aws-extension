import * as zlib from "zlib";
import * as AWS from 'aws-sdk';

const s3 = new AWS.S3();

const bucketName = process.env.S3_BUCKET_NAME || "";

async function appendToS3Object(key: string, text: string): Promise<void> {
    try {
        // Check if the object exists
        const getObjectParams = {
            Bucket: bucketName,
            Key: key
        };
        const getObjectResult = await s3.getObject(getObjectParams).promise();

        // If object exists, append text to existing content
        let existingText = getObjectResult.Body.toString();
        existingText += text;

        // Update the object with the appended text
        const putObjectParams = {
            Bucket: bucketName,
            Key: key,
            Body: existingText
        };
        await s3.putObject(putObjectParams).promise();
    } catch (error) {
        // If getObject throws an error, the object doesn't exist, so create it
        if (error.code === 'NoSuchKey') {
            const putObjectParams = {
                Bucket: bucketName,
                Key: key,
                Body: text
            };
            await s3.putObject(putObjectParams).promise();
        } else {
            throw error;
        }
    }
}



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
    let message = ``;
    lists.forEach((item) => {
        message += `${item.message}\n`;
    } );

    const endpointName = logGroup.split('/').pop();

    appendToS3Object(`logs/${endpointName}.log`, message)
        .then(() => console.log('Text appended to S3 object successfully'))
        .catch(error => console.error('Error appending text to S3 object:', error));

  }

  return {}
}

