import os
from datetime import datetime

import boto3

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
    status = ""
    if stage == 'Training':
        print("Status check for training not implemented yet!")
    elif stage == 'Deployment':
        name = event_payload['endpoint_name']
        endpoint_details = describe_endpoint(name)
        status = endpoint_details['EndpointStatus']
        if status == 'InService':
            current_time = str(datetime.now())
            event_payload['message'] = 'Deployment completed for endpoint "{}".'.format(name)
            check_and_enable_autoscaling(DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME,
                                         {'EndpointDeploymentJobId': endpoint_deployment_job_id}, 'autoscaling',
                                         endpoint_name, 'prod')
            update_endpoint_job_table(endpoint_deployment_job_id, 'endpoint_name', endpoint_name)
            update_endpoint_job_table(endpoint_deployment_job_id, 'endTime', current_time)
        elif status == 'Creating':
            update_endpoint_job_table(endpoint_deployment_job_id, 'endpoint_name', endpoint_name)
        elif status == 'Failed':
            failure_reason = endpoint_details['FailureReason']
            event_payload['message'] = 'Deployment failed for endpoint "{}". {}'.format(name, failure_reason)
            update_endpoint_job_table(endpoint_deployment_job_id, 'endpoint_name', endpoint_name)
        elif status == 'RollingBack':
            event_payload[
                'message'] = 'Deployment failed for endpoint "{}", rolling back to previously deployed version.'.format(
                name)
            update_endpoint_job_table(endpoint_deployment_job_id, 'endpoint_name', endpoint_name)
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
        raise Exception(
            f"Failed to get the endpoint deployment job item with endpoint deployment job id: {endpoint_deployment_job_id}")

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
        PolicyName="Invocations-ScalingPolicy",
        ServiceNamespace="sagemaker",  # The namespace of the AWS service that provides the resource.
        ResourceId='endpoint/' + endpoint_name + '/variant/' + variant_name,  # Endpoint name
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",  # SageMaker supports only Instance Count
        PolicyType="TargetTrackingScaling",  # 'StepScaling'|'TargetTrackingScaling'
        TargetTrackingScalingPolicyConfiguration={
            "TargetValue": 5.0,
            # The target value for the metric. - here the metric is - SageMakerVariantInvocationsPerInstance
            "CustomizedMetricSpecification": {
                "MetricName": "ApproximateBacklogSizePerInstance",
                "Namespace": "AWS/SageMaker",
                "Dimensions": [{"Name": "EndpointName", "Value": endpoint_name}],
                "Statistic": "Average",
            },
            "ScaleInCooldown": 600,
            # The cooldown period helps you prevent your Auto Scaling group from launching or terminating
            "ScaleOutCooldown": 300
            # ScaleOutCooldown - The amount of time, in seconds, after a scale out activity completes before another
            # scale out activity can start.
        },
    )

    step_policy_response = client.put_scaling_policy(
        PolicyName="HasBacklogWithoutCapacity-ScalingPolicy",
        ServiceNamespace="sagemaker",  # The namespace of the service that provides the resource.
        ResourceId='endpoint/' + endpoint_name + '/variant/' + variant_name,
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",  # SageMaker supports only Instance Count
        PolicyType="StepScaling",  # 'StepScaling' or 'TargetTrackingScaling'
        StepScalingPolicyConfiguration={
            "AdjustmentType": "ChangeInCapacity",
            # Specifies whether the ScalingAdjustment value in the StepAdjustment property is an absolute number or a
            # percentage of the current capacity.
            "MetricAggregationType": "Average",  # The aggregation type for the CloudWatch metrics.
            "Cooldown": 600,  # The amount of time, in seconds, to wait for a previous scaling activity to take effect.
            "StepAdjustments":  # A set of adjustments that enable you to scale based on the size of the alarm breach.
                [
                    {
                        "MetricIntervalLowerBound": 0,
                        "ScalingAdjustment": 1
                    }
                ]
        },
    )

    cw_client = boto3.client('cloudwatch')

    cw_client.put_metric_alarm(
        AlarmName='stable-diffusion-hasbacklogwithoutcapacity-alarm',
        MetricName='HasBacklogWithoutCapacity',
        Namespace='AWS/SageMaker',
        Statistic='Average',
        EvaluationPeriods=2,
        DatapointsToAlarm=2,
        Threshold=1,
        ComparisonOperator='GreaterThanOrEqualToThreshold',
        TreatMissingData='missing',
        Dimensions=[
            {'Name': 'EndpointName', 'Value': endpoint_name},
        ],
        Period=60,
        AlarmActions=[step_policy_response['PolicyARN']]
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
        raise (e)
    return response
