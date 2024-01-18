import os
import time
from dotenv import load_dotenv


import boto3
import sagemaker

def create_model(name, image_url, model_data_url):
    """ Create SageMaker model.
    Args:
        name (string): Name to label model with
        image_url (string): Registry path of the Docker image that contains the model algorithm
        model_data_url (string): URL of the model artifacts created during training to download to container
    Returns:
        (None)
    """
    try:
        # delete model at first
        print("delete model at first")
        sagemaker.delete_model(ModelName=name)
        time.sleep(5)
        print("start create model...")
        sagemaker.create_model(
            ModelName=name,
            PrimaryContainer={
                'Image': image_url,
                'ModelDataUrl': model_data_url
            },
            ExecutionRoleArn=EXECUTION_ROLE
        )
    except Exception as e:
        print(e)
        print('Unable to create model.')
        raise(e)

def create_endpoint_config(endpoint_config_name, s3_output_path, model_name, initial_instance_count, instance_type):
    """ Create SageMaker endpoint configuration.
    Args:
        endpoint_config_name (string): Name to label endpoint configuration with.
        model_name (string): The name of model to host.
        initial_instance_count (integer): Number of instances to launch initially.
        instance_type (string): the ML compute instance type.
    Returns:
        (None)
    """
    try:
        print("delete endpoint_config at first")
        sagemaker.delete_endpoint_config(EndpointConfigName=endpoint_config_name)
        time.sleep(5)
        print("start create endpoint config...")
        sagemaker.create_endpoint_config(
            EndpointConfigName=endpoint_config_name,
            # AsyncInferenceConfig={
            #     "OutputConfig": {
            #         "S3OutputPath": s3_output_path,
            #         # "NotificationConfig": {
            #         #     "SuccessTopic": ASYNC_SUCCESS_TOPIC,
            #         #     "ErrorTopic": ASYNC_ERROR_TOPIC 
            #         # }
            #     }
            # },
            ProductionVariants=[
                {
                    'VariantName': 'prod',
                    'ModelName': model_name,
                    'InitialInstanceCount': initial_instance_count,
                    'InstanceType': instance_type
                }
            ]
        )
    except Exception as e:
        print(e)
        print('Unable to create endpoint configuration.')
        raise(e)

def create_endpoint(endpoint_name, config_name):
    """ Create SageMaker endpoint with input endpoint configuration.
    Args:
        endpoint_name (string): Name of endpoint to create.
        config_name (string): Name of endpoint configuration to create endpoint with.
    Returns:
        (None)
    """
    try:
        print("delete endpoint at first")
        sagemaker.delete_endpoint(EndpointName=endpoint_name)
        time.sleep(5)
        print("start create endpoint ...")
        sagemaker.create_endpoint(
            EndpointName=endpoint_name,
            EndpointConfigName=config_name
        )
    except Exception as e:
        print(e)
        print('Unable to create endpoint.')
        raise(e)

def describe_endpoint(name):
    """ Describe SageMaker endpoint identified by input name.
    Args:
        name (string): Name of SageMaker endpoint to describe.
    Returns:
        (dict)
        Dictionary containing metadata and details about the status of the endpoint.
    """
    try:
        response = sagemaker.describe_endpoint(
            EndpointName=name
        )
    except Exception as e:
        print(e)
        print('Unable to describe endpoint.')
        raise(e)
    return response


sagemaker = boto3.client('sagemaker')
s3_resource = boto3.resource('s3')
s3_client = boto3.client('s3')

load_dotenv()

EXECUTION_ROLE = os.environ['Role']
# ASYNC_SUCCESS_TOPIC = os.environ["SNS_INFERENCE_SUCCESS"]
# ASYNC_ERROR_TOPIC = os.environ["SNS_INFERENCE_ERROR"]
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')
# "002224604296.dkr.ecr.us-west-2.amazonaws.com/stable-diffusion-aws-extension/aigc-app-vto:latest"
INFERENCE_ECR_IMAGE_URL = os.environ.get("INFERENCE_ECR_IMAGE_URL")

# deploy endpoint
print(f"start deploy realtime endpoint")

endpoint_deployment_id = "aigc-app-vto"
sagemaker_model_name = f"infer-model-{endpoint_deployment_id}"
sagemaker_endpoint_config = f"infer-config-{endpoint_deployment_id}"
sagemaker_endpoint_name = f"infer-endpoint-{endpoint_deployment_id}"

image_url = INFERENCE_ECR_IMAGE_URL 
model_data_url = f"s3://{S3_BUCKET_NAME}/data/model.tar.gz"

s3_output_path = "N/A"

initial_instance_count = 1
instance_type = "ml.g5.xlarge"

print('Creating model resource ...')

create_model(sagemaker_model_name, image_url, model_data_url)
print('Creating endpoint configuration...')

create_endpoint_config(sagemaker_endpoint_config, s3_output_path, sagemaker_model_name, initial_instance_count, instance_type)
print('There is no existing endpoint for this model. Creating new model endpoint...')

create_endpoint(sagemaker_endpoint_name, sagemaker_endpoint_config)

# wait until ep is deployed
status = "Creating"

while status != "InService":
    status = describe_endpoint(sagemaker_endpoint_name)['EndpointStatus']
    if status == "Failed" or status == "RollingBack":
        raise Exception(f"Error! endpoint in status {status}")
    if status == "InService":
        print(f"Current status is {status}, finish endpoint deployed")
        break
    else:
        print(f"Current status is {status}, creating endpoint...")
    time.sleep(180)