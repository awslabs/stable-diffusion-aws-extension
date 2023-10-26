# todo: this is not done yet
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
                    "Resource": "*"
                }
            ]
        },
        "context": {
            "username": "alvndaiyan",
            "role": "IT Operator,Designer"
        }
    }
