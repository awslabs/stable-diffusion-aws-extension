import json

import boto3
from aws_lambda_powertools import Tracer

tracer = Tracer()
sns = boto3.client('sns')


def get_topic_arn(sns_topic):
    response = sns.list_topics()
    for topic in response['Topics']:
        if topic['TopicArn'].split(':')[-1] == sns_topic:
            return topic['TopicArn']
    return None


@tracer.capture_method
def send_message_to_sns(message_json, sns_topic):
    sns_topic_arn = get_topic_arn(sns_topic)
    if sns_topic_arn is None:
        print(f"No topic found with name {sns_topic}")
        return {
            'statusCode': 404,
            'body': json.dumps('No topic found')
        }

    sns.publish(
        TopicArn=sns_topic_arn,
        Message=json.dumps(message_json),
        Subject='Inference Error occurred Information',
    )

    print(f"Message sent to SNS topic: {sns_topic}")
    return {
        'statusCode': 200,
        'body': json.dumps('Message sent successfully')
    }
