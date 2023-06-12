import json
import boto3

s3_resource = boto3.resource('s3')

def get_bucket_and_key(s3uri):
    pos = s3uri.find('/', 5)
    bucket = s3uri[5 : pos]
    key = s3uri[pos + 1 : ]
    return bucket, key

output_location = "s3://stable-diffusion-aws-extension-aigcbucketa457cb49-1r9svjhqjplic/sagemaker_output/ef218ab7-098c-4231-b14e-3edafad67ebb.out"

bucket, key = get_bucket_and_key(output_location)
obj = s3_resource.Object(bucket, key)
body = obj.get()['Body'].read().decode('utf-8') 
json_body = json.loads(body)

print(f"caption is {type(json_body['caption'])}")
