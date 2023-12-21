# todo: this is not done yet
import base64

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

    encode_type = 'utf-8'
    username = ''
    if event['authorizationToken']:
        username = base64.b16decode(event['authorizationToken'].replace('Bearer ', '').encode(encode_type)).decode(
            encode_type)
        print(f'decoded username: {username}')

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
            "username": username,
            "role": "IT Operator,Designer"
        }
    }
