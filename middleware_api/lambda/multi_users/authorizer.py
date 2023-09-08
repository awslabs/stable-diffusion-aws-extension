
# {
#   'type': 'TOKEN',
#   'methodArn': 'arn:aws:execute-api:us-east-1:648149843064:bcxifc5mkb/prod/GET/users',
#   'authorizationToken': 'test'
#  }

permission_mapper = {
    'create': 'POST',
    'update': '[POST|PUT]',
    'delete': '[POST|DELETE]',
    'get': 'GET',
}


def auth(event, context):
    print(context)
    print(event['methodArn'])
    print(event['authorizationToken'])
    return {
        "principalId": "user",
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": "Allow",
                    "Resource": event['methodArn']
                }
            ]
        },
        "context": {
            "username": "alvndaiyan",
            "role": "exampleValue"
        }
    }
