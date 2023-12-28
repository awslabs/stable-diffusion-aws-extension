import logging
import os
from datetime import datetime

import boto3
from common.ddb_service.client import DynamoDbUtilsService
from endpoints.delete_endpoints import get_endpoint_with_endpoint_name
from libs.enums import EndpointStatus

sagemaker_endpoint_table = os.environ.get('DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME')
user_table = os.environ.get('MULTI_USER_TABLE')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')
ASYNC_SUCCESS_TOPIC = os.environ.get('SNS_INFERENCE_SUCCESS')
ASYNC_ERROR_TOPIC = os.environ.get('SNS_INFERENCE_ERROR')
INFERENCE_ECR_IMAGE_URL = os.environ.get("INFERENCE_ECR_IMAGE_URL")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
sagemaker = boto3.client('sagemaker')
ddb_service = DynamoDbUtilsService(logger=logger)


# lambda: handle sagemaker events
def handler(event, context):
    logger.info(event)
    endpoint_name = event['detail']['EndpointName']
    endpoint_status = event['detail']['EndpointStatus']

    endpoint = get_endpoint_with_endpoint_name(endpoint_name)

    if not endpoint:
        # maybe the endpoint is not created by sde or already deleted
        logger.error(f"No matching DynamoDB record found for endpoint: {endpoint_name}")
        return {'statusCode': 200}

    endpoint_deployment_job_id = endpoint['EndpointDeploymentJobId']

    business_status = get_business_status(endpoint_status)

    update_endpoint_field(endpoint_deployment_job_id, 'endpoint_status', business_status)

    # update the instance count if the endpoint is not deleting or deleted
    if business_status not in [EndpointStatus.DELETING.value, EndpointStatus.DELETED.value]:
        status = sagemaker.describe_endpoint(EndpointName=endpoint_name)
        logger.info(f"Endpoint status: {status}")
        if 'ProductionVariants' in status:
            instance_count = status['ProductionVariants'][0]['CurrentInstanceCount']
            update_endpoint_field(endpoint_deployment_job_id, 'current_instance_count', instance_count)
    else:
        # sometime sagemaker don't send deleted event, so just use deleted status when deleting
        update_endpoint_field(endpoint_deployment_job_id, 'endpoint_status', EndpointStatus.DELETED.value)
        update_endpoint_field(endpoint_deployment_job_id, 'current_instance_count', 0)

    # if endpoint is deleted, update the instance count to 0 and delete the config and model
    if business_status == EndpointStatus.DELETED.value:
        try:
            endpoint_config_name = event['detail']['EndpointConfigName']
            model_name = event['detail']['ModelName']
            sagemaker.delete_endpoint_config(EndpointConfigName=endpoint_config_name)
            sagemaker.delete_model(ModelName=model_name)
        except Exception as e:
            logger.error(f"error deleting endpoint config and model with exception: {e}")

    if business_status == EndpointStatus.IN_SERVICE.value:
        # if it is the first time in service
        if 'endTime' not in endpoint:
            check_and_enable_autoscaling(endpoint, 'prod')

        current_time = str(datetime.now())
        update_endpoint_field(endpoint_deployment_job_id, 'endTime', current_time)

    if business_status == EndpointStatus.FAILED.value:
        update_endpoint_field(endpoint_deployment_job_id, 'error', event['FailureReason'])

    return {'statusCode': 200}


def check_and_enable_autoscaling(item, variant_name):
    autoscaling = item['autoscaling']['BOOL']
    endpoint_name = item['endpoint_name']['S']
    max_instance_number = item['max_instance_number']['S']

    logger.info(f"autoscaling: {autoscaling}")
    logger.info(f"endpoint_name: {endpoint_name}")
    logger.info(f"max_instance_number: {max_instance_number}")

    if str(autoscaling) == 'True':
        if max_instance_number.isdigit():
            enable_autoscaling(endpoint_name, variant_name, 0, int(max_instance_number))
        else:
            logger.info(f"the max_number field is not digit, just fallback to 1")
            enable_autoscaling(endpoint_name, variant_name, 0, 1)
    else:
        logger.info(f'autoscaling_enabled is {autoscaling}, no need to enable autoscaling')


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
            "ScaleInCooldown": 180,
            # The cooldown period helps you prevent your Auto Scaling group from launching or terminating
            "ScaleOutCooldown": 60
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
            "Cooldown": 180,  # The amount of time, in seconds, to wait for a previous scaling activity to take effect.
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


def update_endpoint_field(endpoint_deployment_job_id, field_name, field_value):
    logger.info(f"Updating DynamoDB {field_name} to {field_value} for: {endpoint_deployment_job_id}")
    ddb_service.update_item(
        table=sagemaker_endpoint_table,
        key={'EndpointDeploymentJobId': endpoint_deployment_job_id['S']},
        field_name=field_name,
        value=field_value
    )


def get_business_status(status):
    """
    Convert SageMaker endpoint status to business status
    :param status: EventBridge event status(upper case)
    :return: business status
    """
    switcher = {
        "IN_SERVICE": EndpointStatus.IN_SERVICE.value,
        "CREATING": EndpointStatus.CREATING.value,
        "DELETED": EndpointStatus.DELETED.value,
        "FAILED": EndpointStatus.FAILED.value,
        "UPDATING": EndpointStatus.UPDATING.value,
        "DELETING": EndpointStatus.DELETING.value,
    }
    return switcher.get(status, status)
