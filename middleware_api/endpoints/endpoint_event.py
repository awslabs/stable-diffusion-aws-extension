import json
import logging
import os
from datetime import datetime

import boto3
from aws_lambda_powertools import Tracer

from common.util import record_seconds_metrics, endpoint_clean
from inferences.inference_libs import update_table_by_pk
from libs.data_types import Endpoint
from libs.enums import EndpointStatus, EndpointType, ServiceType
from libs.utils import get_endpoint_by_name

lambda_client = boto3.client('lambda')

tracer = Tracer()
sagemaker_endpoint_table = os.environ.get('ENDPOINT_TABLE_NAME')

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)

autoscaling_client = boto3.client('application-autoscaling')
cw_client = boto3.client('cloudwatch')
sagemaker = boto3.client('sagemaker')

esd_version = os.environ.get("ESD_VERSION")
cool_down_period = 15 * 60  # 15 minutes

s3_bucket_name = os.environ.get('S3_BUCKET_NAME')
s3 = boto3.resource('s3')
bucket = s3.Bucket(s3_bucket_name)
aws_region = os.environ.get('AWS_REGION')


# lambda: handle sagemaker events
@tracer.capture_lambda_handler
def handler(event, context):
    logger.info(json.dumps(event))
    endpoint_name = event['detail']['EndpointName']
    endpoint_status = event['detail']['EndpointStatus']
    current_time = datetime.now().isoformat()

    try:
        endpoint = get_endpoint_by_name(endpoint_name)

        business_status = get_business_status(endpoint_status)

        update_endpoint_field(endpoint, 'endpoint_status', business_status)

        if business_status == EndpointStatus.UPDATING.value:
            update_endpoint_field(endpoint, 'startTime', current_time)

        if business_status == EndpointStatus.IN_SERVICE.value:
            update_endpoint_field(endpoint, 'endTime', current_time)

            if endpoint.service_type == 'sd':
                service_type = ServiceType.SD.value
            else:
                service_type = ServiceType.Comfy.value

            record_seconds_metrics(start_time=endpoint.startTime,
                                   metric_name='EndpointReadySeconds',
                                   service=service_type)

            # if it is the first time in service
            if not endpoint.endTime:
                check_and_enable_autoscaling(endpoint, 'prod')

        # update the instance count if the endpoint is not deleting or deleted
        if business_status not in [EndpointStatus.DELETING.value, EndpointStatus.DELETED.value]:
            status = sagemaker.describe_endpoint(EndpointName=endpoint_name)
            logger.info(f"Endpoint status: {status}")
            if 'ProductionVariants' in status:
                instance_count = status['ProductionVariants'][0]['CurrentInstanceCount']
                update_endpoint_field(endpoint, 'current_instance_count', instance_count)
        else:
            endpoint_clean(endpoint)

        if business_status == EndpointStatus.FAILED.value:
            update_endpoint_field(endpoint, 'error', event['FailureReason'])

    except Exception as e:
        logger.error(e, exc_info=True)

    return {'statusCode': 200}


def check_and_enable_autoscaling(ep: Endpoint, variant_name):
    if ep.autoscaling:
        enable_autoscaling(ep, variant_name)
    else:
        logger.info(f'no need to enable autoscaling')


@tracer.capture_method
def enable_autoscaling(ep: Endpoint, variant_name):
    tracer.put_annotation("variant_name", variant_name)
    max_instance_number = int(ep.max_instance_number)

    min_instance_number = 0
    if ep.endpoint_type == EndpointType.RealTime.value:
        min_instance_number = 1

    if ep.min_instance_number is not None:
        min_instance_number = int(ep.min_instance_number)

    # Register scalable target
    response = autoscaling_client.register_scalable_target(
        ServiceNamespace='sagemaker',
        ResourceId='endpoint/' + ep.endpoint_name + '/variant/' + variant_name,
        ScalableDimension='sagemaker:variant:DesiredInstanceCount',
        MinCapacity=min_instance_number,
        MaxCapacity=max_instance_number,
    )
    logger.info(f"Register scalable target response: {response}")

    if ep.endpoint_type == EndpointType.Async.value:
        enable_autoscaling_async(ep, variant_name)

    if ep.endpoint_type == EndpointType.RealTime.value:
        enable_autoscaling_real_time(ep, variant_name)


def enable_autoscaling_async(ep: Endpoint, variant_name):
    target_value = 3

    # Define scaling policy
    response = autoscaling_client.put_scaling_policy(
        PolicyName=f"{ep.endpoint_name}-Invocations-ScalingPolicy",
        ServiceNamespace="sagemaker",  # The namespace of the AWS service that provides the resource.
        ResourceId='endpoint/' + ep.endpoint_name + '/variant/' + variant_name,  # Endpoint name
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",  # SageMaker supports only Instance Count
        PolicyType="TargetTrackingScaling",  # 'StepScaling'|'TargetTrackingScaling'
        TargetTrackingScalingPolicyConfiguration={
            "TargetValue": target_value,
            # The target value for the metric. - here the metric is - SageMakerVariantInvocationsPerInstance
            "CustomizedMetricSpecification": {
                "MetricName": "ApproximateBacklogSizePerInstance",
                "Namespace": "AWS/SageMaker",
                "Dimensions": [{"Name": "EndpointName", "Value": ep.endpoint_name}],
                "Statistic": "Average",
            },
            "ScaleInCooldown": 180,
            # The cooldown period helps you prevent your Auto Scaling group from launching or terminating
            "ScaleOutCooldown": 60
            # ScaleOutCooldown - The amount of time, in seconds, after a scale out activity completes before another
            # scale out activity can start.
        },
    )
    logger.info(f"Put scaling policy response")
    logger.info(json.dumps(response))
    alarms = response.get('Alarms')
    for alarm in alarms:
        alarm_name = alarm.get('AlarmName')
        logger.info(f"Alarm name: {alarm_name}")
        response = cw_client.describe_alarms(
            AlarmNames=[alarm_name]
        )
        logger.info(f"Describe alarm response")
        logger.info(response)
        comparison_operator = response.get('MetricAlarms')[0]['ComparisonOperator']
        if comparison_operator == "LessThanThreshold":
            period = cool_down_period  # 15 minutes
            evaluation_periods = 4
            datapoints_to_alarm = 4
            target_value = 1
        else:
            period = 30
            evaluation_periods = 1
            datapoints_to_alarm = 1
            target_value = 3
        response = cw_client.put_metric_alarm(
            AlarmName=alarm_name,
            Namespace='AWS/SageMaker',
            MetricName='ApproximateBacklogSizePerInstance',
            Statistic="Average",
            Period=period,
            EvaluationPeriods=evaluation_periods,
            DatapointsToAlarm=datapoints_to_alarm,
            Threshold=target_value,
            ComparisonOperator=comparison_operator,
            AlarmActions=response.get('MetricAlarms')[0]['AlarmActions'],
            Dimensions=[{'Name': 'EndpointName', 'Value': ep.endpoint_name}]
        )
        logger.info(f"Put metric alarm response")
        logger.info(response)

    step_policy_response = autoscaling_client.put_scaling_policy(
        PolicyName=f"{ep.endpoint_name}-HasBacklogWithoutCapacity-ScalingPolicy",
        ServiceNamespace="sagemaker",  # The namespace of the service that provides the resource.
        ResourceId='endpoint/' + ep.endpoint_name + '/variant/' + variant_name,
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
    logger.info(f"Put step scaling policy response: {step_policy_response}")

    cw_client.put_metric_alarm(
        AlarmName=f'{ep.endpoint_name}-HasBacklogWithoutCapacity-Alarm',
        MetricName='HasBacklogWithoutCapacity',
        Namespace='AWS/SageMaker',
        Statistic='Average',
        Period=30,
        EvaluationPeriods=1,
        DatapointsToAlarm=1,
        Threshold=1,
        ComparisonOperator='GreaterThanOrEqualToThreshold',
        TreatMissingData='missing',
        Dimensions=[
            {'Name': 'EndpointName', 'Value': ep.endpoint_name},
        ],
        AlarmActions=[step_policy_response['PolicyARN']]
    )
    logger.info(f"Put metric alarm response: {step_policy_response}")

    logger.info(f"Autoscaling has been enabled for the endpoint: {ep.endpoint_name}")


@tracer.capture_method
def enable_autoscaling_real_time(ep: Endpoint, variant_name):
    tracer.put_annotation("variant_name", variant_name)
    target_value = 5

    # Define scaling policy
    response = autoscaling_client.put_scaling_policy(
        PolicyName=f"{ep.endpoint_name}-Invocations-ScalingPolicy",
        ServiceNamespace="sagemaker",  # The namespace of the AWS service that provides the resource.
        ResourceId='endpoint/' + ep.endpoint_name + '/variant/' + variant_name,  # Endpoint name
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",  # SageMaker supports only Instance Count
        PolicyType="TargetTrackingScaling",  # 'StepScaling'|'TargetTrackingScaling'
        TargetTrackingScalingPolicyConfiguration={
            "TargetValue": target_value,
            "PredefinedMetricSpecification":
                {
                    "PredefinedMetricType": "SageMakerVariantInvocationsPerInstance"
                },
            "ScaleInCooldown": 180,
            # The cooldown period helps you prevent your Auto Scaling group from launching or terminating
            "ScaleOutCooldown": 60
            # ScaleOutCooldown - The amount of time, in seconds, after a scale out activity completes before another
            # scale out activity can start.
        },
    )
    logger.info(f"Put scaling policy response")
    logger.info(json.dumps(response))
    alarms = response.get('Alarms')
    for alarm in alarms:
        alarm_name = alarm.get('AlarmName')
        logger.info(f"Alarm name: {alarm_name}")
        response = cw_client.describe_alarms(
            AlarmNames=[alarm_name]
        )
        logger.info(f"Describe alarm response")
        logger.info(response)
        comparison_operator = response.get('MetricAlarms')[0]['ComparisonOperator']
        if comparison_operator == "LessThanThreshold":
            period = cool_down_period  # 15 minutes
            evaluation_periods = 4
            datapoints_to_alarm = 4
            target_value = 1
        else:
            period = 30
            evaluation_periods = 1
            datapoints_to_alarm = 1
            target_value = 5
        response = cw_client.put_metric_alarm(
            AlarmName=alarm_name,
            Namespace='AWS/SageMaker',
            MetricName='InvocationsPerInstance',
            Statistic="Sum",
            Period=period,
            EvaluationPeriods=evaluation_periods,
            DatapointsToAlarm=datapoints_to_alarm,
            Threshold=target_value,
            ComparisonOperator=comparison_operator,
            AlarmActions=response.get('MetricAlarms')[0]['AlarmActions'],
            Dimensions=[
                {'Name': 'EndpointName', 'Value': ep.endpoint_name},
                {'Name': 'VariantName', 'Value': 'prod'},
            ]
        )
        logger.info(f"Put metric alarm response")
        logger.info(response)

    logger.info(f"Autoscaling has been enabled for the endpoint: {ep.endpoint_name}")


def update_endpoint_field(ep: Endpoint, field_name, field_value):
    update_table_by_pk(
        table_name=sagemaker_endpoint_table,
        pk='EndpointDeploymentJobId',
        id=ep.EndpointDeploymentJobId,
        key=field_name,
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
