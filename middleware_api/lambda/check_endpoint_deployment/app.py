import boto3
import os
from datetime import datetime

DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME = os.environ.get('DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME')

sagemaker = boto3.client('sagemaker')
ddb_client = boto3.resource('dynamodb')
endpoint_deployment_table = ddb_client.Table(DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME)

def lambda_handler(event, context):
    # Parse the input data
    print(f"event is {event}")
    event_payload = event["Payload"]
    stage = event_payload['stage']
    endpoint_deployment_job_id = event_payload['endpoint_deployment_id']
    endpoint_name = event_payload['endpoint_name']
    if stage == 'Training':
        print("Status check for training not implemented yet!")
    elif stage == 'Deployment':
        name = event_payload['endpoint_name']
        endpoint_details = describe_endpoint(name)
        status = endpoint_details['EndpointStatus']
        if status == 'InService':
            current_time = str(datetime.now())
            event_payload['message'] = 'Deployment completed for endpoint "{}".'.format(name)
            check_and_enable_autoscaling(DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME, {'EndpointDeploymentJobId': endpoint_deployment_job_id}, 'autoscaling', endpoint_name, 'prod')
            update_endpoint_job_table(endpoint_deployment_job_id,'endpoint_name', endpoint_name)
            update_endpoint_job_table(endpoint_deployment_job_id,'endpoint_status', status)
            update_endpoint_job_table(endpoint_deployment_job_id,'endTime', current_time)
            update_endpoint_job_table(endpoint_deployment_job_id,'status', 'success')
        elif status == 'Creating':
            update_endpoint_job_table(endpoint_deployment_job_id,'endpoint_name', endpoint_name)
            update_endpoint_job_table(endpoint_deployment_job_id,'endpoint_status', status) 
        elif status == 'Failed':
            failure_reason = endpoint_details['FailureReason']
            event_payload['message'] = 'Deployment failed for endpoint "{}". {}'.format(name, failure_reason)
            update_endpoint_job_table(endpoint_deployment_job_id,'endpoint_name', endpoint_name)
            update_endpoint_job_table(endpoint_deployment_job_id,'endpoint_status', status)
            update_endpoint_job_table(endpoint_deployment_job_id,'status', 'failed')
        elif status == 'RollingBack':
            event_payload['message'] = 'Deployment failed for endpoint "{}", rolling back to previously deployed version.'.format(name)
            update_endpoint_job_table(endpoint_deployment_job_id,'endpoint_name', endpoint_name)
            update_endpoint_job_table(endpoint_deployment_job_id,'endpoint_status', status)
    event_payload['status'] = status
    return event_payload

def update_endpoint_job_table(endpoint_deployment_job_id, key, value):
    # Update the inference DDB for the job status
    response = endpoint_deployment_table.get_item(
        Key={
            "EndpointDeploymentJobId": endpoint_deployment_job_id,
        })
    endpoint_resp = response['Item']
    if not endpoint_resp:
        raise Exception(f"Failed to get the endpoint deployment job item with endpoint deployment job id: {endpoint_deployment_job_id}")

    response = endpoint_deployment_table.update_item(
        Key={
            "EndpointDeploymentJobId": endpoint_deployment_job_id,
        },
        UpdateExpression=f"set #k = :r",
        ExpressionAttributeNames={'#k': key},
        ExpressionAttributeValues={':r': value},
        ReturnValues="UPDATED_NEW"
    )

def get_ddb_value(table_name, key, field_name):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    try:
        response = table.get_item(Key=key)
    except Exception as e:
        print(str(e))
        return None
    else:
        item = response['Item']
        return item.get(field_name, None)

def enable_autoscaling(endpoint_name, variant_name, low_value, high_value):
    client = boto3.client('application-autoscaling')

    # Register scalable target
    response = client.register_scalable_target(
        ServiceNamespace='sagemaker',
        ResourceId='endpoint/' + endpoint_name + '/variant/' + variant_name,
        ScalableDimension='sagemaker:variant:DesiredInstanceCount',
        MinCapacity=low_value,
        MaxCapacity=high_value,
    )

    # Define scaling policy
    response = client.put_scaling_policy(
        PolicyName='StableDiffusionDefaultScalingPolicy',
        ServiceNamespace='sagemaker',
        ResourceId='endpoint/' + endpoint_name + '/variant/' + variant_name,
        ScalableDimension='sagemaker:variant:DesiredInstanceCount',
        PolicyType='TargetTrackingScaling',
        TargetTrackingScalingPolicyConfiguration={
            'TargetValue': 2.0,
            'PredefinedMetricSpecification': {
                'PredefinedMetricType': 'SageMakerVariantInvocationsPerInstance',
            },
            'ScaleInCooldown': 300,
            'ScaleOutCooldown': 300
        }
    )
    print(f"Autoscaling has been enabled for the endpoint: {endpoint_name}")

def check_and_enable_autoscaling(table_name, key, field_name, endpoint_name, variant_name):
    autoscaling_enabled = get_ddb_value(table_name, key, field_name)
    if str(autoscaling_enabled) == 'True':
        max_number = get_ddb_value(table_name, key, 'max_instance_number')
        if max_number.isdigit():
            enable_autoscaling(endpoint_name, variant_name, 0, int(max_number))
        else:
            print(f"the max_number field is not digit, just fallback to 1")
            enable_autoscaling(endpoint_name, variant_name, 0, 1)
    else:
        print(f'autoscaling_enabled is {autoscaling_enabled}, no need to enable autoscaling')


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
